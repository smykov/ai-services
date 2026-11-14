# Separate from tts-gpu: Kokoro needs torch >= 2.6, XTTS (TTS 0.22) is pinned to torch 2.4.
# The cu124 wheels bring their own CUDA runtime, so the image needs only the NVIDIA driver.
FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir --default-timeout=300 torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124

COPY tts-kokoro/requirements.txt .
RUN pip install --no-cache-dir --default-timeout=300 -r requirements.txt \
 && pip install --no-cache-dir https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl

COPY tts-kokoro/worker.py tts-kokoro/synthesizer.py ./
COPY shared/ ./shared/

CMD ["python3", "worker.py"]
