FROM nvidia/cuda:12.2-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y python3.11 python3-pip && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY tts-gpu/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY tts-gpu/worker.py tts-gpu/synthesizer.py ./
COPY shared/ ./shared/

CMD ["python3", "worker.py"]
