# Zenvort

A file conversion API built with FastAPI and Celery. Accept file uploads, convert using FFmpeg, Gotenberg, Pillow, PyMuPDF, Tesseract and more, store results on Cloudflare R2, and return a download URL. Jobs are processed asynchronously via **Celery + Redis**.

---

## Architecture

```
                     ┌──────────────┐
                     │   Client     │
                     │  CLI / SDK   │
                     └──────┬───────┘
                            │ HTTPS
                            ▼
┌───────────────────────────────────────────────────────┐
│              api (FastAPI, :8000)                    │
│                                                       │
│  /v1/convert  /v1/pdf/*  /v1/ocr  /v1/image/*        │
│  /v1/media/*  /v1/jobs  /v1/admin/*                  │
│                                                       │
│  SQLite (aiosqlite) → /data/zenvort.db                │
│  Celery dispatch → Redis                              │
└─────────────────────────────┬─────────────────────────┘
                              │
         ┌────────────────────┴──────────────────┐
         ▼                                        ▼
┌─────────────────────┐               ┌─────────────────────────┐
│   worker (Celery)   │               │    Cloudflare R2        │
│  - FFmpeg           │               │    outputs/{jobId}/     │
│  - Gotenberg        │               │    Presigned URLs       │
│  - Pillow           │               └─────────────────────────┘
│  - PyMuPDF          │
│  - Tesseract        │               ┌─────────────────────────┐
│  - Pandoc           │               │  redis (:6379)          │
└─────────────────────┘               │  Celery broker/backend   │
                                     └─────────────────────────┘
```

**Services:**
- `api` — FastAPI REST API (port 8000)
- `worker` — Celery async job processor
- `redis` — Redis 7 (Celery broker)
- `gotenberg` — Gotenberg/LibreOffice (document conversion)

---

## Quick Start

```bash
# Clone
git clone https://github.com/originlhibrid/zenvort.git
cd zenvort

# Configure
cp .env.example .env
# Edit .env with your R2 credentials and ADMIN_SECRET

# Start
docker-compose up -d

# Check health
curl http://localhost:8000/v1/health

# Create API key
curl -X POST http://localhost:8000/v1/admin/keys \
  -H "admin_secret: YOUR_ADMIN_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"name": "test-key", "tier": "free"}'
```

---

## API Endpoints

### Public
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/v1/health` | Health check (no auth) |

### File Conversion (requires `X-API-Key`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/convert` | Convert between formats |
| `POST` | `/v1/pdf/merge` | Merge multiple PDFs |
| `POST` | `/v1/pdf/split` | Split PDF by page ranges |
| `POST` | `/v1/pdf/rotate` | Rotate PDF pages |
| `POST` | `/v1/pdf/watermark` | Add text watermark |
| `POST` | `/v1/pdf/stamp` | Add image stamp |
| `POST` | `/v1/pdf/encrypt` | Encrypt with password |
| `POST` | `/v1/pdf/decrypt` | Decrypt with password |
| `POST` | `/v1/pdf/compress` | Compress PDF |
| `POST` | `/v1/pdf/metadata` | Read/write metadata |
| `POST` | `/v1/pdf/bookmarks` | Read/write bookmarks |
| `POST` | `/v1/pdf/flatten` | Flatten form fields |
| `POST` | `/v1/pdf/pdfa` | Convert to PDF/A |
| `POST` | `/v1/ocr` | OCR on images/PDFs |
| `POST` | `/v1/image/convert` | Convert image format |
| `POST` | `/v1/image/resize` | Resize image |
| `POST` | `/v1/media/convert` | Convert audio/video |
| `GET` | `/v1/jobs/{job_id}` | Get job status |
| `GET` | `/v1/jobs/{job_id}?download=true` | Download result |

### Admin (requires `admin_secret`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/admin/keys` | Create new API key |
| `GET` | `/v1/admin/keys` | List all keys |
| `DELETE` | `/v1/admin/keys/{key_id}` | Deactivate key |
| `GET` | `/v1/admin/usage/{key_id}` | Usage logs |
| `POST` | `/v1/admin/reset-daily` | Reset daily counters |

---

## Rate Limits

| Tier | Daily Limit |
|------|-------------|
| free | 50 requests |
| pro | 500 requests |
| enterprise | 10,000 requests |

---

## Supported Formats

**Documents:** docx, pptx, odt, xlsx, ods, odp, md, html, rtf, txt, pdf

**Images:** jpg, jpeg, png, webp, avif, bmp, tiff, gif, svg

**Audio:** mp3, wav, ogg, flac

**Video:** mp4, avi, mov, webm

---

## Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `ADMIN_SECRET` | Yes | — | Admin authentication |
| `DB_PATH` | No | `/data/zenvort.db` | SQLite database path |
| `TEMP_DIR` | No | `/tmp/zenvort` | Temp file directory |
| `REDIS_URL` | No | `redis://redis:6379/0` | Redis connection |
| `GOTENBERG_URL` | No | `http://gotenberg:3000` | Gotenberg service |
| `R2_ACCOUNT_ID` | Yes | — | Cloudflare R2 account |
| `R2_ACCESS_KEY_ID` | Yes | — | R2 access key |
| `R2_SECRET_ACCESS_KEY` | Yes | — | R2 secret key |
| `R2_BUCKET_NAME` | No | `zenvort` | R2 bucket name |
| `R2_ENDPOINT_URL` | No | `https://{account_id}.r2.cloudflarestorage.com` | R2 endpoint |
| `MAX_FILE_SIZE_MB` | No | `100` | Max upload size |
| `PRESIGNED_EXPIRY_SECONDS` | No | `3600` | Download URL expiry |

---

## Example Usage

```bash
# Create API key
ADMIN_SECRET="your-secure-secret"
curl -X POST http://localhost:8000/v1/admin/keys \
  -H "admin_secret: $ADMIN_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"name": "dev-key", "tier": "free"}'

# Convert PDF to DOCX
curl -X POST http://localhost:8000/v1/convert \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "file=@document.pdf" \
  -F "to=docx"

# Check job status
curl http://localhost:8000/v1/jobs/JOB_ID \
  -H "X-API-Key: YOUR_API_KEY"

# Download result
curl "http://localhost:8000/v1/jobs/JOB_ID?download=true" \
  -H "X-API-Key: YOUR_API_KEY" \
  -o output.docx

# OCR an image
curl -X POST http://localhost:8000/v1/ocr \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "file=@scan.jpg" \
  -F "language=eng"

# Merge PDFs
curl -X POST http://localhost:8000/v1/pdf/merge \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "files=@page1.pdf" \
  -F "files=@page2.pdf"

# Compress PDF
curl -X POST http://localhost:8000/v1/pdf/compress \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "file=@large.pdf" \
  -F "quality=high"
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| API | FastAPI + Uvicorn |
| Task Queue | Celery + Redis |
| Database | SQLite (aiosqlite) |
| Document Conversion | Gotenberg (LibreOffice), Pandoc |
| PDF Processing | PyMuPDF, pikepdf, pdf2docx |
| Image Processing | Pillow, CairoSVG, img2pdf |
| Media Processing | FFmpeg |
| OCR | Tesseract + pytesseract |
| Storage | Cloudflare R2 (S3-compatible) |
| Rate Limiting | slowapi |

---

## File Structure

```
zenvort/
├── app/
│   ├── main.py              # FastAPI app, lifespan, health
│   ├── config.py            # Pydantic settings
│   ├── db.py                # SQLite operations (aiosqlite)
│   ├── auth.py              # API key verification
│   ├── storage.py           # R2 upload/download
│   ├── response.py          # Error response helpers
│   ├── worker.py            # Celery app definition
│   ├── tasks.py             # 5 Celery tasks
│   ├── routers/
│   │   ├── admin.py         # Admin endpoints
│   │   ├── convert.py       # Generic conversion
│   │   ├── pdf.py           # PDF operations (12 endpoints)
│   │   ├── ocr.py           # OCR endpoint
│   │   ├── image.py         # Image operations
│   │   ├── media.py         # Media conversion
│   │   └── jobs.py          # Job status
│   ├── handlers/
│   │   ├── documents.py     # Gotenberg conversion
│   │   ├── pdf_ops.py       # PyMuPDF operations
│   │   ├── images.py        # Pillow/CairoSVG
│   │   ├── media.py         # FFmpeg
│   │   └── ocr.py           # Tesseract
│   └── utils/
│       ├── temp.py          # Temp file management
│       ├── validation.py    # Rate limiting, file size
│       └── formats.py        # Format constants
├── Dockerfile              # Multi-stage for api + worker
├── docker-compose.yml       # 4 services
├── Makefile                 # Common commands
├── requirements.txt
├── .env.example
└── README.md
```

---

## Security

| Feature | Implementation |
|---------|---------------|
| **API Key Auth** | SHA256 hash stored in DB, raw key returned only on creation |
| **Admin Auth** | `admin_secret` query param (or `X-Admin-Secret` header) |
| **Rate Limiting** | Daily limits per tier (50/500/10000) |
| **File Size** | Configurable max, enforced before processing |
| **Active Key Check** | Revoked keys rejected immediately |

---

## Development

```bash
# Local development
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Run worker
celery -A app.worker.celery_app worker --loglevel=info

# Run with Docker
docker-compose up --build
```

---

## License

MIT