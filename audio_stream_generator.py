from pipe_process import pipe_process

def audio_stream_generator(url: str,format: str):
    """
    yt-dlp (URL only) -> ffmpeg -> stdout (NO DISK, SABR SAFE)
    """
    
    if format == "mp3":
        ffmpeg_args = ["-vn", "-c:a", "libmp3lame", "-b:a", "192k"]
        mime = "audio/mpeg"
        ext = "mp3"
    else:  # fmp4
        ffmpeg_args = [
            "-vn",
            "-c:a", "aac",
            "-movflags", "frag_keyframe+empty_moov+faststart"
        ]
        mime = "audio/mp4"
        ext = "m4a"

    ytdlp_cmd = [
        "yt-dlp",
        "--no-playlist",
        "-f", "bestaudio",
        "-o", "-",
        url
    ]

    ffmpeg_cmd = [
        "ffmpeg",
        "-i", "pipe:0",
        *ffmpeg_args,
        "-f", "mp4" if ext == "m4a" else "mp3",
        "pipe:1"
    ]

    return pipe_process(ytdlp_cmd, ffmpeg_cmd), mime, ext
