FROM python:3.12-slim

RUN apt-get update && apt-get install -y python3-pip && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY surya/requirements.txt .
RUN pip install --default-timeout=300 --no-cache-dir --index-url https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

COPY surya/worker.py surya/reader.py ./
COPY shared/ ./shared/

CMD ["python3", "worker.py"]
