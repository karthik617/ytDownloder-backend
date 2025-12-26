import subprocess

def pipe_process(ytdlp_cmd, ffmpeg_cmd):
    print("Starting yt-dlp")
    print(f"Command: {' '.join(ytdlp_cmd)}")  # See exact command
    
    ytdlp_proc = subprocess.Popen(
        ytdlp_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE  # CAPTURE ERRORS
    )

    print("Starting ffmpeg")
    ffmpeg_proc = subprocess.Popen(
        ffmpeg_cmd,
        stdin=ytdlp_proc.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE  # CAPTURE ERRORS
    )

    ytdlp_proc.stdout.close()

    # Collect errors
    import threading
    
    ytdlp_errors = []
    ffmpeg_errors = []
    
    def collect_ytdlp_errors():
        for line in ytdlp_proc.stderr:
            error_line = line.decode('utf-8', errors='ignore')
            ytdlp_errors.append(error_line)
            print(f"[yt-dlp]: {error_line.strip()}")
    
    def collect_ffmpeg_errors():
        for line in ffmpeg_proc.stderr:
            error_line = line.decode('utf-8', errors='ignore')
            ffmpeg_errors.append(error_line)
            print(f"[ffmpeg]: {error_line.strip()}")
    
    threading.Thread(target=collect_ytdlp_errors, daemon=True).start()
    threading.Thread(target=collect_ffmpeg_errors, daemon=True).start()

    try:
        chunk_count = 0
        while True:
            chunk = ffmpeg_proc.stdout.read(1024 * 64)
            if not chunk:
                break
            chunk_count += 1
            if chunk_count % 10 == 0:
                print(f"Streamed {chunk_count} chunks")
            yield chunk
    finally:
        print(f"Total chunks yielded: {chunk_count}")
        ytdlp_proc.kill()
        ffmpeg_proc.kill()
        
        # Print any collected errors
        if ytdlp_errors:
            print("=== yt-dlp ERRORS ===")
            print(''.join(ytdlp_errors))
        if ffmpeg_errors:
            print("=== ffmpeg ERRORS ===")
            print(''.join(ffmpeg_errors))