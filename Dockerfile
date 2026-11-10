FROM python:3.12-slim

WORKDIR /app

# Install system dependencies including FFmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    p7zip-full \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Filter out PyQt6 for headless Docker container
RUN grep -v "PyQt6" requirements.txt > requirements-headless.txt && \
    pip install --no-cache-dir -r requirements-headless.txt

COPY . .

EXPOSE 8463 54321

VOLUME ["/downloads", "/config"]

ENTRYPOINT ["python", "main_headless.py", "--host", "0.0.0.0", "--port", "8463"]
