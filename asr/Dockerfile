FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y python3.11 python3-pip ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY asr/requirements.txt .
RUN pip install --default-timeout=300 --no-cache-dir -r requirements.txt

COPY asr/worker.py asr/transcriber.py ./
COPY shared/ ./shared/

CMD ["python3", "worker.py"]
