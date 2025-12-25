import subprocess

def pipe_process(ytdlp_cmd, ffmpeg_cmd):
    """
    Runs yt-dlp -> ffmpeg -> stdout in a streaming way.
    Yields chunks of bytes suitable for StreamingResponse.
    """
    # Start yt-dlp process
    ytdlp_proc = subprocess.Popen(
        ytdlp_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Start ffmpeg process, reading yt-dlp output
    ffmpeg_proc = subprocess.Popen(
        ffmpeg_cmd,
        stdin=ytdlp_proc.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Close yt-dlp stdout in parent so ffmpeg can detect EOF
    ytdlp_proc.stdout.close()

    try:
        while True:
            chunk = ffmpeg_proc.stdout.read(1024 * 32)
            if not chunk:
                break
            yield chunk
    finally:
        ytdlp_proc.kill()
        ffmpeg_proc.kill()
