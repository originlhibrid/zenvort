# ⚡ Zenvort

**A blazing-fast file conversion API powered by FastAPI & Celery**

Convert documents, images, audio, video, and PDFs with a single REST call. Built for scalability with async processing, Cloudflare R2 storage, and intelligent rate limiting.

---

## 🚀 Quick Start

```bash
git clone https://github.com/originlhibrid/zenvort.git
cd zenvort

# Configure environment
cp .env.example .env
# Edit .env with your R2 credentials and ADMIN_SECRET

# Start services
docker compose up -d

# Health check
curl http://localhost:8000/v1/health
```

---

## 📐 Architecture

```
                           ┌─────────────┐
                           │   Client    │
                           │  CLI / SDK  │
                           └──────┬──────┘
                                  │ HTTPS
                                  ▼
              ┌───────────────────────────────────────┐
              │            api (FastAPI)              │
              │                                        │
              │  /v1/convert  /v1/pdf/*  /v1/ocr      │
              │  /v1/image/*  /v1/media/*            │
              │                                        │
              │  SQLite + Redis                       │
              └──────────────┬────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
   ┌──────────┐       ┌──────────┐       ┌──────────────┐
   │  Worker  │       │   R2     │       │    Redis     │
   │ (Celery) │       │ Storage  │       │   Broker     │
   └──────────┘       └──────────┘       └──────────────┘
```

| Service | Port | Purpose |
|---------|------|---------|
| `api` | 8000 | FastAPI REST API |
| `worker` | — | Celery async processor |
| `redis` | 6379 | Message broker & backend |
| `gotenberg` | 3000 | LibreOffice document conversion |

---

## 📡 Endpoints

### 🔓 Public

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/v1/health` | Health check (no auth) |

---

### 📄 Conversion (Requires `X-API-Key`)

#### General Conversion
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/convert` | Convert between any supported format |

#### PDF Operations
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/pdf/merge` | Merge multiple PDFs |
| `POST` | `/v1/pdf/split` | Split by page ranges |
| `POST` | `/v1/pdf/rotate` | Rotate pages |
| `POST` | `/v1/pdf/watermark` | Add text watermark |
| `POST` | `/v1/pdf/stamp` | Add image stamp |
| `POST` | `/v1/pdf/encrypt` | Password protect |
| `POST` | `/v1/pdf/decrypt` | Remove encryption |
| `POST` | `/v1/pdf/compress` | Reduce file size |
| `POST` | `/v1/pdf/metadata` | Read/write metadata |
| `POST` | `/v1/pdf/bookmarks` | Manage bookmarks |
| `POST` | `/v1/pdf/flatten` | Flatten form fields |
| `POST` | `/v1/pdf/pdfa` | Convert to PDF/A |

#### Media & OCR
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/ocr` | OCR on images/PDFs |
| `POST` | `/v1/image/convert` | Convert image format |
| `POST` | `/v1/image/resize` | Resize image |
| `POST` | `/v1/media/convert` | Convert audio/video |

#### Jobs
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/v1/jobs/{job_id}` | Get job status |
| `GET` | `/v1/jobs/{job_id}?download=true` | Download result |

---

### 🔐 Admin (Requires `admin_secret`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/admin/keys` | Create API key |
| `GET` | `/v1/admin/keys` | List all keys |
| `DELETE` | `/v1/admin/keys/{key_id}` | Deactivate key |
| `GET` | `/v1/admin/usage/{key_id}` | View usage logs |
| `POST` | `/v1/admin/reset-daily` | Reset daily counters |

---

## 📦 Supported Formats

| Category | Formats |
|----------|---------|
| **Documents** | docx, pptx, odt, xlsx, ods, odp, md, html, rtf, txt, pdf |
| **Images** | jpg, jpeg, png, webp, avif, bmp, tiff, gif, svg |
| **Audio** | mp3, wav, ogg, flac |
| **Video** | mp4, avi, mov, webm |

---

## 💡 Usage Examples

### Create API Key
```bash
curl -X POST "http://localhost:8000/v1/admin/keys?admin_secret=YOUR_ADMIN_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-app", "tier": "free"}'
```

### Convert Document to PDF
```bash
curl -X POST http://localhost:8000/v1/convert \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "file=@document.docx" \
  -F "to=pdf"
```

### OCR an Image
```bash
curl -X POST http://localhost:8000/v1/ocr \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "file=@scan.jpg" \
  -F "language=eng"
```

### Merge PDFs
```bash
curl -X POST http://localhost:8000/v1/pdf/merge \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "files=@page1.pdf" \
  -F "files=@page2.pdf"
```

### Check Job Status
```bash
curl http://localhost:8000/v1/jobs/JOB_ID \
  -H "X-API-Key: YOUR_API_KEY"
```

---

## ⚙️ Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ADMIN_SECRET` | ✅ | — | Admin authentication |
| `R2_ACCOUNT_ID` | ✅ | — | Cloudflare R2 account ID |
| `R2_ACCESS_KEY_ID` | ✅ | — | R2 access key |
| `R2_SECRET_ACCESS_KEY` | ✅ | — | R2 secret key |
| `DB_PATH` | | `/data/zenvort.db` | SQLite database path |
| `TEMP_DIR` | | `/tmp/zenvort` | Temp file directory |
| `REDIS_URL` | | `redis://redis:6379/0` | Redis connection |
| `GOTENBERG_URL` | | `http://gotenberg:3000` | Gotenberg URL |
| `MAX_FILE_SIZE_MB` | | `100` | Max upload size (MB) |
| `PRESIGNED_EXPIRY_SECONDS` | | `3600` | Download URL expiry |

---

## 📊 Rate Limits

| Tier | Daily Requests | Use Case |
|------|----------------|----------|
| 🆓 free | 50 | Development, testing |
| 💎 pro | 500 | Small projects |
| 🏢 enterprise | 10,000 | Production workloads |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **API** | FastAPI + Uvicorn |
| **Task Queue** | Celery + Redis |
| **Database** | SQLite (aiosqlite) |
| **Document Conversion** | Gotenberg, Pandoc |
| **PDF Processing** | PyMuPDF, pikepdf, pdf2docx |
| **Image Processing** | Pillow, CairoSVG, img2pdf |
| **Media Processing** | FFmpeg |
| **OCR** | Tesseract |
| **Storage** | Cloudflare R2 |
| **Rate Limiting** | slowapi |

---

## 🧪 Development

```bash
# Local setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run API
uvicorn app.main:app --reload --port 8000

# Run worker (separate terminal)
celery -A app.worker.celery_app worker --loglevel=info --concurrency=2
```

---

## 📁 Project Structure

```
zenvort/
├── app/
│   ├── main.py              # FastAPI app & health endpoints
│   ├── config.py            # Pydantic settings
│   ├── db.py                # SQLite operations
│   ├── auth.py              # API key verification
│   ├── storage.py           # R2 S3 client
│   ├── worker.py            # Celery app definition
│   ├── tasks.py             # 5 async task handlers
│   ├── routers/
│   │   ├── admin.py         # Key & usage management
│   │   ├── convert.py       # Generic conversion
│   │   ├── pdf.py           # 12 PDF endpoints
│   │   ├── ocr.py           # OCR processing
│   │   ├── image.py         # Image operations
│   │   ├── media.py         # Audio/video
│   │   └── jobs.py          # Status & download
│   ├── handlers/            # Processing engines
│   │   ├── documents.py     # Gotenberg + Pandoc
│   │   ├── pdf_ops.py       # PyMuPDF operations
│   │   ├── images.py        # Pillow + CairoSVG
│   │   ├── media.py         # FFmpeg wrapper
│   │   └── ocr.py           # Tesseract wrapper
│   └── utils/
│       ├── temp.py          # Job temp directories
│       ├── validation.py    # Rate limits & size
│       └── formats.py       # Format constants
├── Dockerfile              # Multi-stage build
├── docker-compose.yml      # 4-service orchestration
├── Makefile                # Dev commands
├── requirements.txt
└── .env.example
```

---

## 🔒 Security

| Feature | Implementation |
|---------|---------------|
| API Key Auth | SHA256 hashed, returned only on creation |
| Admin Auth | Secret-based with header/param support |
| Rate Limiting | Per-key daily counters by tier |
| File Size Limits | Configurable max, enforced pre-processing |
| Key Revocation | Immediate rejection of revoked keys |

---

## 📜 License

MIT License — free for personal and commercial use.