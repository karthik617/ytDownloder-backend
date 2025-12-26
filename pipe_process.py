import subprocess
import os
def pipe_process(ytdlp_cmd, ffmpeg_cmd):
    """
    Runs yt-dlp -> ffmpeg -> stdout in a streaming way.
    Yields chunks of bytes suitable for StreamingResponse.
    """
    print("starting yt-dlp process")
    # Start yt-dlp process
    ytdlp_proc = subprocess.Popen(
        ytdlp_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    print('output from yt-dlp:', ytdlp_proc.stdout)
    print('Size of yt-dlp output:', os.fstat(ytdlp_proc.stdout.fileno()).st_size)
    print('error from yt-dlp:', ytdlp_proc.stderr)
    print("starting ffmpeg process")
    # Start ffmpeg process, reading yt-dlp output
    ffmpeg_proc = subprocess.Popen(
        ffmpeg_cmd,
        stdin=ytdlp_proc.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    print('output from ffmpeg:', ffmpeg_proc.stdout)
    print('Size of ffmpeg output:', os.fstat(ffmpeg_proc.stdout.fileno()).st_size)
    print('error from ffmpeg:', ffmpeg_proc.stderr)
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
