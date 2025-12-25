from pipe_process import pipe_process

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
        "-o", "-",
        url
    ]

    ffmpeg_cmd = [
        "ffmpeg",
        "-i", "pipe:0",
        "-c", "copy",
        "-movflags", "frag_keyframe+empty_moov+faststart",
        "-f", "mp4",
        "pipe:1"
    ]

    return pipe_process(ytdlp_cmd, ffmpeg_cmd)
