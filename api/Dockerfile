FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libmagic1 && rm -rf /var/lib/apt/lists/*

COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./api/
COPY worker/ ./worker/

ENV PYTHONPATH=/app
ENV DB_PATH=/data/zenvort.db

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "3000"]
