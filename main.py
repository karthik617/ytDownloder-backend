from fastapi import FastAPI, HTTPException, Query,Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter
from fastapi.middleware.cors import CORSMiddleware
import shutil
import redis
import json
import os
import base64
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
from audio_stream_generator import audio_stream_generator
from video_stream_generator import video_stream_generator
from playlist_stream_generator import download_to_temp, zip_stream
from utils.cookie_rotation import download_with_cookie_rotation

load_dotenv()

app = FastAPI(title="YouTube Media Downloader API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5175", "https://ytdownloader-frontend.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"]
)
COOKIE_DIR=os.environ.get("COOKIE_DIR")
@app.on_event("startup")
def startup():
    cookie_dir = COOKIE_DIR
    os.makedirs(cookie_dir, exist_ok=True)

    for i in range(1, 5):
        env_key = f"YT_COOKIE_{i}"
        if env_key in os.environ:
            path = f"{cookie_dir}/yt_{i}.txt"
            with open(path, "wb") as f:
                f.write(base64.b64decode(os.environ[env_key]))
# Connect to Redis
REDIS_HOST = os.environ.get("REDIS_HOST")
REDIS_PORT = os.environ.get("REDIS_PORT")
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD")

r = None
if REDIS_HOST and REDIS_PORT:
    try:
        r = redis.Redis(
            host=REDIS_HOST,
            port=int(REDIS_PORT),
            password=REDIS_PASSWORD,
            decode_responses=True,
            socket_connect_timeout=1
        )
        r.ping()
    except redis.RedisError:
        print("Redis unavailable")
        r = None

CACHE_TTL = int(os.environ.get("CACHE_TTL")) or 3600
MAX_DURATION = int(os.environ.get("MAX_DURATION")) or 30 * 60  # 30 min
MAX_VIDEOS = int(os.environ.get("MAX_VIDEOS")) or 10  # safety limit for playlists

# Counter: total downloads per type
DOWNLOAD_COUNTER = Counter(
    "downloads_total", "Number of downloads", ["type"]  # type=audio/video/playlist
)

# Counter: cache hits
CACHE_HITS = Counter("cache_hits_total", "Number of cache hits")

# Counter: cache misses
CACHE_MISSES = Counter("cache_misses_total", "Number of cache misses")

instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
)
instrumentator.instrument(app).expose(app, endpoint="/metrics")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded"}
    )

def normalize_playlist_url(url: str) -> str:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "list" in qs:
        return f"https://www.youtube.com/playlist?list={qs['list'][0]}"
    return url

def get_video_info(url: str, opts: dict):
    cache_key = f"video_info:{url}"

    # Try cache read
    try:
        if r:
            r.ping()
            cached = r.get(cache_key)
            if cached:
                CACHE_HITS.inc()
                return json.loads(cached)
    except redis.RedisError:
        pass  # Redis unavailable → continue

    CACHE_MISSES.inc()
    # Fetch from YouTube
    # with yt_dlp.YoutubeDL(opts) as ydl:
    #     info = ydl.extract_info(url, download=False)
    try:
        info =  download_with_cookie_rotation(url,opts,False)
    except Exception as e:
        raise HTTPException(400, str(e))

    if not info:
        raise ValueError("Invalid video URL")

    # Try cache write (DO NOT FAIL REQUEST)
    try:
        if r:
            r.set(cache_key, json.dumps(info), ex=CACHE_TTL)
    except redis.RedisError:
        pass

    return info

def validate_video(url: str):
    ydl_opts = {
        "noplaylist": True,
        "skip_download": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android"]
            }
        }
    }

    info = get_video_info(url,ydl_opts)

    if not info:
        raise HTTPException(400, "Invalid URL")

    if info.get("duration", 0) > MAX_DURATION:
        raise HTTPException(413, "Video too long")

    title = info.get("title", "video")

    return info, title

@app.get("/download/audio")
@limiter.limit("7/minute")
def download_audio(request: Request, url: str = Query(...),format: str = Query("mp3", enum=["mp3", "fmp4"])):
    info, title = validate_video(url)

    safe_title = "".join(c for c in title if c.isalnum() or c in " -_")

    stream, mime, ext = audio_stream_generator(url, format)

    return StreamingResponse(
       stream,
        media_type=mime,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_title}.{ext}"',
            "Cache-Control": "no-store",
            "Accept-Ranges": "bytes",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )


@app.get("/download/video")
@limiter.limit("5/minute")
def download_video(request: Request, url: str = Query(...),quality: str = Query("auto", enum=["auto", "720p", "1080p"])):
    info, title = validate_video(url)

    safe_title = "".join(c for c in title if c.isalnum() or c in " -_")

    return StreamingResponse(
        video_stream_generator(url,quality),
        media_type="video/mp4",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_title}.mp4"',
            "Cache-Control": "no-store",
            "Accept-Ranges": "bytes",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )

@app.get("/download/playlist")
@limiter.limit("3/minute")
def download_playlist(
    request: Request, 
    url: str = Query(...),
    audio_only: bool = Query(True)
):  
    if "list=RD" in url:
        raise HTTPException(
            400,
            "YouTube Mix playlists are not supported"
        )
    playlist_url = normalize_playlist_url(url)

    ydl_opts = {
        "skip_download": True,
        "extract_flat": True,   # 🔑 ensures entries exist
        "js_runtimes": {
            "node": {}   
        }   
    }

    # with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    #     info = ydl.extract_info(playlist_url, download=False)
    try:
        info =  download_with_cookie_rotation(playlist_url,ydl_opts,False)
    except Exception as e:
        raise HTTPException(400, str(e))
    title = info.get("title", "playlist")
    safe_title = "".join(c for c in title if c.isalnum() or c in " -_")

    if not info or "entries" not in info:
        raise HTTPException(400, "Invalid playlist URL")

    entries = [e for e in info["entries"] if e][:MAX_VIDEOS]

    if not entries:
        raise HTTPException(400, "Playlist is empty")

    temp_dirs = []
    all_files = []

    try:
        for entry in entries:
            video_url = f"https://www.youtube.com/watch?v={entry['id']}"
            temp_dir, files = download_to_temp(
                video_url,
                audio_only=audio_only,
                title=entry.get("title", entry["id"])
            )
            temp_dirs.append(temp_dir)
            all_files.extend(files)

        return StreamingResponse(
            zip_stream(all_files),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_title}.zip"',
                "Cache-Control": "no-store",
                "Accept-Ranges": "bytes",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    finally:
        for d in temp_dirs:
            shutil.rmtree(d, ignore_errors=True)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def index():
    return {"status": "ok", "message": "YouTube Media Downloader API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
