import subprocess

def pipe_process(ytdlp_cmd, ffmpeg_cmd):
    """
    yt-dlp -> ffmpeg -> Streaming generator
    SAFE for Render / Docker / Mobile
    """

    print("Starting yt-dlp")
    ytdlp_proc = subprocess.Popen(
        ytdlp_cmd,
        stdout=subprocess.PIPE,
        stderr=None
    )

    print("Starting ffmpeg")
    ffmpeg_proc = subprocess.Popen(
        ffmpeg_cmd,
        stdin=ytdlp_proc.stdout,
        stdout=subprocess.PIPE,
        stderr=None 
    )

    # Close yt-dlp stdout in parent
    ytdlp_proc.stdout.close()

    try:
        while True:
            chunk = ffmpeg_proc.stdout.read(1024 * 64)
            if not chunk:
                break
            yield chunk
    finally:
        ytdlp_proc.kill()
        ffmpeg_proc.kill()
