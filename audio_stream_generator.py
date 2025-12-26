from pipe_process import pipe_process
from utils.cookie_pool import CookiePool

cookie_pool = CookiePool()

def audio_stream_generator(url: str, format: str):
    if format == "mp3":
        mime = "audio/mpeg"
        ext = "mp3"
        audio_format = "mp3"
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", "pipe:0",
            "-vn",
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            "-f", "mp3",
            "pipe:1"
        ]
    else:  # fmp4 (m4a)
        mime = "audio/mp4"
        ext = "mp4"
        audio_format = "m4a"
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", "pipe:0",
            "-vn",
            "-c", "copy",
            "-movflags", "frag_keyframe+empty_moov+faststart",
            "-f", "mp4",
            "pipe:1"
        ]

    ytdlp_cmd = [
        "yt-dlp",
        "--no-playlist",
        "-f", "bestaudio",
        "--extract-audio",
        "--audio-format", audio_format,
        "-o", "-"
    ]

    cookie_file = cookie_pool.get_cookie()
    print("Using cookie: [AUDIO]", cookie_file)
    if cookie_file:
        ytdlp_cmd += ["--cookies", cookie_file]

    ytdlp_cmd.append(url)

    return pipe_process(ytdlp_cmd, ffmpeg_cmd), mime, ext
