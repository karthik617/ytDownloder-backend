import os
import tempfile
import yt_dlp
from zipfile import ZipFile
from io import BytesIO


def download_to_temp(url: str, audio_only: bool, title: str):
    """Download a single video/audio to a temp file and return path."""
    temp_dir = tempfile.mkdtemp()
    ext = "mp3" if audio_only else "mp4"
    output_template = os.path.join(temp_dir, f"{title}.{ext}")
    print("OUTPUT TEMPLATE", output_template)
    ydl_opts = {
        "format": "bestaudio/best" if audio_only else "best",
        "outtmpl": output_template,
        "quiet": True,
        "ignoreerrors": True,
        "noplaylist": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }] if audio_only else []
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
    
    # List all downloaded files
    files = []
    for f in os.listdir(temp_dir):
        files.append(os.path.join(temp_dir, f))
    
    return temp_dir, files

def zip_stream(file_paths):
    """Stream files as a ZIP archive."""
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, "w") as zip_file:
        for fpath in file_paths:
            zip_file.write(fpath, arcname=os.path.basename(fpath))
    zip_buffer.seek(0)
    return zip_buffer