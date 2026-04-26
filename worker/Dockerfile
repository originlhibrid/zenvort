FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./api/
COPY worker/ ./worker/
COPY db/ ./db/

ENV PYTHONPATH=/app

RUN mkdir -p /tmp/zenvort

CMD celery -A worker.celery_app worker --loglevel=info --concurrency=${WORKER_CONCURRENCY:-3}
