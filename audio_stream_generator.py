from pipe_process import pipe_process
from utils.cookie_pool import CookiePool

cookie_pool = CookiePool()

def audio_stream_generator(url: str, format: str):
    if format == "mp3":
        mime = "audio/mpeg"
        ext = "mp3"
        ffmpeg_cmd = [
            "ffmpeg",
            "-loglevel", "error",
            "-i", "pipe:0",
            "-vn",
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            "-f", "mp3",
            "pipe:1"
        ]
    else:  # m4a
        mime = "audio/mp4"
        ext = "mp4"
        ffmpeg_cmd = [
            "ffmpeg",
            "-loglevel", "error",
            "-i", "pipe:0",
            "-vn",
            "-c:a", "copy",
            "-movflags", "frag_keyframe+empty_moov+faststart",
            "-f", "mp4",
            "pipe:1"
        ]

    ytdlp_cmd = [
        "yt-dlp",
        "--no-playlist",
        "--no-progress",
        "-f", "bestaudio",
        "-o", "-",
        "--js-runtimes", "deno"
    ]

    cookie_file = cookie_pool.get_cookie()

    # ADD THESE DEBUG LINES:
    import os
    print(f"Cookie file exists: {os.path.exists(cookie_file)}")
    print(f"Cookie file size: {os.path.getsize(cookie_file) if os.path.exists(cookie_file) else 'N/A'}")
    print(f"Cookie file readable: {os.access(cookie_file, os.R_OK)}")
    
    print("Using cookie [AUDIO]:", cookie_file)

    if cookie_file:
        ytdlp_cmd += ["--cookies", cookie_file]

    ytdlp_cmd.append(url)

    return pipe_process(ytdlp_cmd, ffmpeg_cmd), mime, ext
