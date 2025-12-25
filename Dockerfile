FROM python:3.11-slim

# ---- System deps ----
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    ca-certificates \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# ---- yt-dlp (latest) ----
RUN pip install --no-cache-dir -U yt-dlp

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
