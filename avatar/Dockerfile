FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg git libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 --extra-index-url https://download.pytorch.org/whl/cu118
RUN pip install --no-cache-dir openmim mmengine==0.10.7 && \
    pip install --no-cache-dir mmcv==2.0.1 -f https://download.openmmlab.com/mmcv/dist/cu118/torch2.0/index.html && \
    pip install --no-cache-dir mmdet==3.1.0 mmpose==1.1.0

COPY avatar/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# MuseTalk code, pinned; weights are downloaded into the /models volume on first start.
ARG MUSETALK_COMMIT=0a89dec
RUN git clone https://github.com/TMElyralab/MuseTalk.git /opt/MuseTalk && \
    git -C /opt/MuseTalk checkout ${MUSETALK_COMMIT} && rm -rf /opt/MuseTalk/.git /opt/MuseTalk/assets /opt/MuseTalk/data && \
    ln -s /models /opt/MuseTalk/models && ln -s /models/gfpgan /opt/MuseTalk/gfpgan
ENV MUSETALK_DIR=/opt/MuseTalk TORCH_HOME=/models/torch HF_HOME=/models/hf

WORKDIR /app
COPY avatar/worker.py avatar/engine.py avatar/speech_mask.py avatar/weights.py ./
COPY shared/ ./shared/

CMD ["python", "worker.py"]
