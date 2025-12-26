from pipe_process import pipe_process
from utils.cookie_pool import CookiePool

cookie_pool = CookiePool()

def video_stream_generator(url: str, quality: str):
    if quality == "720p":
        fmt = "bv*[height<=720]+ba/best"
    elif quality == "1080p":
        fmt = "bv*[height<=1080]+ba/best"
    else:
        fmt = "bv*+ba/best"

    ytdlp_cmd = [
        "yt-dlp",
        "--no-playlist",
        "-f", fmt,
        "--merge-output-format", "mp4",
        "-o", "-"
    ]

    cookie_file = cookie_pool.get_cookie()
    
    # ADD THESE DEBUG LINES:
    import os
    print(f"Cookie file exists: {os.path.exists(cookie_file)}")
    print(f"Cookie file size: {os.path.getsize(cookie_file) if os.path.exists(cookie_file) else 'N/A'}")
    print(f"Cookie file readable: {os.access(cookie_file, os.R_OK)}")

    print("Using cookie: [VIDEO]", cookie_file)
    if cookie_file:
        ytdlp_cmd += ["--cookies", cookie_file]
    
    ytdlp_cmd.append(url)

    ffmpeg_cmd = [
        "ffmpeg",
        "-i", "pipe:0",
        "-movflags", "frag_keyframe+empty_moov+faststart",
        "-c", "copy",
        "-f", "mp4",
        "pipe:1"
    ]

    return pipe_process(ytdlp_cmd, ffmpeg_cmd)
