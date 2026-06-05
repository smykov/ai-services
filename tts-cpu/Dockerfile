FROM python:3.12-slim

RUN pip install piper-tts

WORKDIR /app

COPY tts-cpu/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY tts-cpu/worker.py tts-cpu/synthesizer.py ./
COPY shared/ ./shared/

CMD ["python3", "worker.py"]
