FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libxcb1 \
    libxcb-shm0 \
    libxcb-xfixes0 \
    libxcb-shape0 \
    libxcb-randr0 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY surya/requirements.txt .
RUN pip install --default-timeout=300 --index-url https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

COPY surya/worker.py surya/reader.py ./
COPY shared/ ./shared/

CMD ["python3", "worker.py"]
