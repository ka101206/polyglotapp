FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libasound2-dev \
    ffmpeg \
    flac \
    espeak-ng \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Bake TTS models into the image so no download happens at runtime.
# HF_TOKEN is optional (anonymous downloads work, just slower / rate-limited).
ARG HF_TOKEN=""
ENV HF_HUB_DISABLE_TELEMETRY=1
RUN HF_TOKEN=${HF_TOKEN} python download_models.py

# Expose FastAPI port
EXPOSE 8081

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8081", "--reload"]
