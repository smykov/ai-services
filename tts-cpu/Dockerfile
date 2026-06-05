FROM python:3.12-slim

RUN apt-get update && apt-get install -y piper-tts && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY tts-cpu/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY tts-cpu/worker.py tts-cpu/synthesizer.py ./
COPY shared/ ./shared/

CMD ["python3", "worker.py"]
