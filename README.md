# ⚡ Zenvort

### Blazing-Fast File Conversion API

---

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Celery-37814A?style=for-the-badge&logo=celery&logoColor=white" alt="Celery">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/Cloudflare%20R2-F38020?style=for-the-badge&logo=cloudflare&logoColor=white" alt="R2">
</p>

<p align="center">
  <strong>Convert documents • Process PDFs • OCR images • Transform media</strong>
</p>

---

## ✨ Features

<div align="center">

| Feature | Description |
|:--------|:------------|
| 📄 **Document Conversion** | docx → pdf, md → html, rtf → docx, and 30+ formats |
| 📑 **PDF Operations** | Merge, split, rotate, watermark, encrypt, compress, PDF/A |
| 🔍 **OCR Engine** | Extract text from images and scanned PDFs |
| 🖼️ **Image Processing** | Convert, resize, compress images |
| 🎬 **Media Conversion** | Audio and video format transformation |
| ⚡ **Async Processing** | Celery workers with Redis broker |
| ☁️ **Cloud Storage** | Automatic upload to Cloudflare R2 |
| 🔐 **API Key Auth** | Secure with SHA256 hashing |
| 📊 **Rate Limiting** | Per-tier daily limits |

</div>

---

## 🚀 Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/originlhibrid/zenvort.git
cd zenvort

# 2. Configure environment
cp .env.example .env
# Edit .env with your R2 credentials and ADMIN_SECRET

# 3. Launch services
docker compose up -d

# 4. Verify health
curl http://localhost:8000/v1/health
```

**Response:**
```json
{"status": "ok", "redis": "ok", "storage": "ok", "worker": "ok"}
```

---

## 🏗️ Architecture

```
                            ╭──────────────────────╮
                            │       Client         │
                            │   cURL / SDK / CLI   │
                            ╰──────────┬───────────╯
                                       │
                              ┌────────▼────────┐
                              │    HTTPS        │
                              │   (port 8000)   │
                              └────────┬────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    │                                     │
             ╭──────▼───────────────────────╮     ╭──────▼───────╮
             │          API Service          │     │    Redis     │
             │         (FastAPI)             │     │   (Broker)   │
             │                               │     ╰──────┬───────╮
             │  ┌─────────────────────────┐  │            │       │
             │  │  Endpoints & Validation │  │            │       │
             │  └────────────┬────────────┘  │            │       │
             │               │               │     ╭──────▼───────▼──╮
             │  ┌────────────▼────────────┐  │     │   Celery Worker  │
             │  │    SQLite Database     │  │     │                   │
             │  └─────────────────────────┘  │     │  • Gotenberg     │
             │               │               │     │  • PyMuPDF       │
             │  ┌────────────▼────────────┐  │     │  • FFmpeg        │
             │  │    Celery Dispatch     │──┼────▶│  • Tesseract     │
             │  └─────────────────────────┘  │     │  • Pillow        │
             ╰──────────────┬─────────────────╯     ╰──────┬───────╯
                            │                              │
                   ╭────────▼───────────╮          ╭───────▼───────╮
                   │    Cloudflare R2    │          │   Gotenberg   │
                   │   (Output Storage) │          │   :3000       │
                   ╰────────────────────╯          ╰──────────────╯
```

| Component | Technology | Purpose |
|-----------|------------|---------|
| `api` | FastAPI + Uvicorn | REST API server |
| `worker` | Celery | Async job processor |
| `redis` | Redis 7 | Message broker & cache |
| `gotenberg` | LibreOffice 8 | Document conversion |

---

## 📡 API Reference

### 🔓 Public Endpoints

| Method | Endpoint | Description |
|:------:|----------|-------------|
| `GET` | `/v1/health` | Service health check |

---

### 📋 Conversion Endpoints

```
POST /v1/convert     → Convert between any supported format
```

| Method | Endpoint | Description |
|:------:|----------|-------------|
| `POST` | `/v1/pdf/merge` | Combine multiple PDFs |
| `POST` | `/v1/pdf/split` | Extract page ranges |
| `POST` | `/v1/pdf/rotate` | Rotate pages (90°, 180°, 270°) |
| `POST` | `/v1/pdf/watermark` | Add text watermark |
| `POST` | `/v1/pdf/stamp` | Add image stamp |
| `POST` | `/v1/pdf/encrypt` | Password protect |
| `POST` | `/v1/pdf/decrypt` | Remove encryption |
| `POST` | `/v1/pdf/compress` | Reduce file size |
| `POST` | `/v1/pdf/metadata` | Read/write metadata |
| `POST` | `/v1/pdf/bookmarks` | Manage bookmarks |
| `POST` | `/v1/pdf/flatten` | Flatten form fields |
| `POST` | `/v1/pdf/pdfa` | Convert to PDF/A format |

---

### 🎨 Media Endpoints

| Method | Endpoint | Description |
|:------:|----------|-------------|
| `POST` | `/v1/ocr` | Extract text via OCR |
| `POST` | `/v1/image/convert` | Image format conversion |
| `POST` | `/v1/image/resize` | Resize with quality control |
| `POST` | `/v1/media/convert` | Audio/Video conversion |

---

### 📊 Job Endpoints

| Method | Endpoint | Description |
|:------:|----------|-------------|
| `GET` | `/v1/jobs/{job_id}` | Get job status |
| `GET` | `/v1/jobs/{job_id}?download=true` | Download output file |

---

### 🔐 Admin Endpoints

| Method | Endpoint | Description |
|:------:|----------|-------------|
| `POST` | `/v1/admin/keys?admin_secret=...` | Create new API key |
| `GET` | `/v1/admin/keys?admin_secret=...` | List all keys |
| `DELETE` | `/v1/admin/keys/{key_id}?admin_secret=...` | Revoke a key |
| `GET` | `/v1/admin/usage/{key_id}?admin_secret=...` | View usage stats |
| `POST` | `/v1/admin/reset-daily?admin_secret=...` | Reset counters |

---

## 📦 Supported Formats

### Documents
```
docx  pptx  odt  xlsx  ods  odp  md  html  rtf  txt  pdf
```

### Images
```
jpg  jpeg  png  webp  avif  bmp  tiff  gif  svg
```

### Audio
```
mp3  wav  ogg  flac
```

### Video
```
mp4  avi  mov  webm
```

---

## 💡 Usage Examples

### 1. Create an API Key

```bash
curl -X POST "http://localhost:8000/v1/admin/keys?admin_secret=YOUR_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-app", "tier": "free"}'
```

**Response:**
```json
{
  "key_id": "abc123...",
  "api_key": "zv_xxxxxxxxxxxxx",
  "name": "my-app",
  "tier": "free"
}
```

### 2. Convert Document to PDF

```bash
curl -X POST http://localhost:8000/v1/convert \
  -H "X-API-Key: zv_xxxxxxxxxxxxx" \
  -F "file=@report.docx" \
  -F "to=pdf"
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "poll_url": "/v1/jobs/550e8400-e29b-41d4-a716-446655440000"
}
```

### 3. OCR a Scanned Document

```bash
curl -X POST http://localhost:8000/v1/ocr \
  -H "X-API-Key: zv_xxxxxxxxxxxxx" \
  -F "file=@scan.jpg" \
  -F "language=eng"
```

### 4. Merge Multiple PDFs

```bash
curl -X POST http://localhost:8000/v1/pdf/merge \
  -H "X-API-Key: zv_xxxxxxxxxxxxx" \
  -F "files=@chapter1.pdf" \
  -F "files=@chapter2.pdf" \
  -F "files=@chapter3.pdf"
```

### 5. Compress a PDF

```bash
curl -X POST http://localhost:8000/v1/pdf/compress \
  -H "X-API-Key: zv_xxxxxxxxxxxxx" \
  -F "file=@large.pdf" \
  -F "quality=high"
```

### 6. Check Job Status

```bash
curl http://localhost:8000/v1/jobs/550e8400-e29b-41d4-a716-446655440000 \
  -H "X-API-Key: zv_xxxxxxxxxxxxx"
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "download_url": "https://...",
  "created_at": "2025-01-01T12:00:00Z"
}
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|:--------:|---------|-------------|
| `ADMIN_SECRET` | ✅ | — | Admin authentication secret |
| `R2_ACCOUNT_ID` | ✅ | — | Cloudflare R2 account ID |
| `R2_ACCESS_KEY_ID` | ✅ | — | R2 access key ID |
| `R2_SECRET_ACCESS_KEY` | ✅ | — | R2 secret access key |
| `R2_BUCKET_NAME` | | `zenvort` | R2 storage bucket |
| `R2_ENDPOINT_URL` | | auto | R2 endpoint URL |
| `DB_PATH` | | `/data/zenvort.db` | SQLite database path |
| `TEMP_DIR` | | `/tmp/zenvort` | Temporary files directory |
| `REDIS_URL` | | `redis://redis:6379/0` | Redis connection URL |
| `GOTENBERG_URL` | | `http://gotenberg:3000` | Gotenberg service URL |
| `MAX_FILE_SIZE_MB` | | `100` | Maximum upload size (MB) |
| `PRESIGNED_EXPIRY_SECONDS` | | `3600` | Download URL expiry (seconds) |

---

## 📊 Rate Limits

| Tier | Daily Limit | Best For |
|------|:-----------:|----------|
| 🆓 **free** | 50 | Development & testing |
| 💎 **pro** | 500 | Small projects |
| 🏢 **enterprise** | 10,000 | Production workloads |

---

## 🛠️ Tech Stack

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                            │
│                      cURL / SDK / CLI                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                        API Layer                             │
│                                                              │
│   FastAPI  ·  Uvicorn  ·  Pydantic  ·  slowapi  ·  SQLite   │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                     Processing Layer                          │
│                                                              │
│   Celery  ·  Redis  ·  Gotenberg  ·  FFmpeg  ·  Tesseract    │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                      Storage Layer                            │
│                                                              │
│          Cloudflare R2  ·  Local File System                 │
└─────────────────────────────────────────────────────────────┘
```

| Category | Technology |
|----------|------------|
| **Framework** | FastAPI 0.136 |
| **Server** | Uvicorn with uvloop |
| **Task Queue** | Celery 5.6 + Redis 7 |
| **Database** | SQLite (async via aiosqlite) |
| **Documents** | Gotenberg (LibreOffice), Pandoc |
| **PDF** | PyMuPDF, pikepdf, pdf2docx, img2pdf |
| **Images** | Pillow, CairoSVG |
| **Media** | FFmpeg |
| **OCR** | Tesseract |
| **Storage** | boto3 (S3-compatible) |
| **Validation** | python-magic |

---

## 🧪 Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run API server
uvicorn app.main:app --reload --port 8000

# Run worker (new terminal)
celery -A app.worker.celery_app worker --loglevel=info --concurrency=2
```

---

## 📁 Project Structure

```
zenvort/
├── app/
│   ├── main.py              # FastAPI app, lifespan, health
│   ├── config.py             # Pydantic settings from env
│   ├── db.py                 # SQLite async operations
│   ├── auth.py               # API key verification
│   ├── storage.py            # R2 S3 client wrapper
│   ├── worker.py             # Celery app instance
│   ├── tasks.py              # 5 Celery task definitions
│   ├── routers/
│   │   ├── admin.py          # Key management & usage
│   │   ├── convert.py        # Generic file conversion
│   │   ├── pdf.py            # 12 PDF operations
│   │   ├── ocr.py            # Text extraction
│   │   ├── image.py          # Image processing
│   │   ├── media.py          # Audio/video
│   │   └── jobs.py           # Status polling & download
│   ├── handlers/
│   │   ├── documents.py     # Gotenberg + Pandoc
│   │   ├── pdf_ops.py        # PyMuPDF operations
│   │   ├── images.py         # Pillow + CairoSVG
│   │   ├── media.py          # FFmpeg wrapper
│   │   └── ocr.py            # Tesseract wrapper
│   └── utils/
│       ├── temp.py           # Temp file cleanup
│       ├── validation.py     # Rate limiting checks
│       └── formats.py        # Format constants
├── Dockerfile               # Multi-stage build
├── docker-compose.yml       # Service orchestration
├── Makefile                 # Development commands
├── requirements.txt         # Python dependencies
├── .env.example             # Environment template
└── README.md                # This file
```

---

## 🔒 Security

| Feature | Implementation |
|---------|----------------|
| **API Keys** | SHA256 hashed in database, raw returned only on creation |
| **Admin Auth** | Secret in header (`X-Admin-Secret`) or query param |
| **Rate Limits** | Daily counters per key, rejected when exceeded |
| **File Size** | Configurable max enforced before processing |
| **Key Revocation** | Revoked keys rejected immediately |
| **CORS** | Configurable allowed origins |

---

## 🐳 Docker Commands

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f api
docker compose logs -f worker

# Scale workers
docker compose up -d --scale worker=4

# Stop services
docker compose down

# Rebuild after changes
docker compose up -d --build
```

---

## 📜 License

<div align="center">

**MIT License** — free for personal and commercial use.

</div>