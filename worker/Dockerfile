FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ffmpeg \
    libmagic1 \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    calibre \
    pandoc \
    && rm -rf /var/lib/apt/lists/*

ENV QT_QPA_PLATFORM=offscreen
ENV DISABLEGPU=1
ENV CALIBRE_NO_NATIVE_FILEDIALOGS=1
ENV CALIBRE_CONFIG_DIRECTORY=/tmp/calibre-config
ENV HOME=/root

RUN mkdir -p /tmp/calibre-config /tmp/calibre-home && \
    chmod 777 /tmp/calibre-config /tmp/calibre-home

COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./api/
COPY worker/ ./worker/
COPY db/ ./db/

ENV PYTHONPATH=/app

RUN mkdir -p /tmp/zenvort

CMD celery -A worker.celery_app worker --loglevel=info --concurrency=${WORKER_CONCURRENCY:-3}
