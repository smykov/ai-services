FROM python:3.12-slim

RUN apt-get update && apt-get install -y piper-tts && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY worker.py synthesizer.py ./

CMD ["python3", "worker.py"]
