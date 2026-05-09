# Zenvort

A CloudConvert-style file conversion SaaS. Accept file uploads via REST API, convert them using FFmpeg, Gotenberg, Pillow, PyMuPDF, Tesseract and more, store results on Cloudflare R2, and return a download URL. Jobs are processed asynchronously via **Celery + Redis**. Files are auto-deleted 20 minutes after conversion.

---

## Architecture

```
                    ┌─────────────────┐
                    │  Any Frontend   │
                    │  Web / Mobile   │
                    │  CLI / SDK      │
                    └────────┬────────┘
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                 api (FastAPI, :3000)                        │
│  /auth  /jobs  /user  /formats  /admin                    │
│  SQLite (aiosqlite) ──▶ /data/zenvort.db                  │
│  Celery task dispatch ──▶ Redis                           │
└───────────────────────────────┬─────────────────────────────┘
                                │
              ┌─────────────────┴─────────────────┐
              ▼                                   ▼
┌─────────────────────────┐        ┌─────────────────────────┐
│  worker (Celery, Redis) │        │    Cloudflare R2         │
│  - FFmpeg (video/audio) │        │    inputs/{jobId}/       │
│  - Gotenberg (LibreOffice)  │   │    outputs/{jobId}/     │
│  - Pillow (images)      │        │    Auto-deleted 20 min   │
│  - PyMuPDF (PDF→image) │        └─────────────────────────┘
│  - Tesseract (OCR)     │
│  - Calibre, Pandoc     │
└─────────────────────────┘
```

**Services:**
- `api` — FastAPI REST API (port 3000)
- `worker` — Celery async job processor
- `redis` — Redis 7 (port 6379)
- `gotenberg` — Gotenberg/LibreOffice (port 3000)

---

## Tech Stack

Python 3.12 · FastAPI · aiosqlite · SQLite · Celery · Redis · Gotenberg (LibreOffice) · FFmpeg · Pillow · PyMuPDF · Tesseract · Calibre · Pandoc · CairoSVG · pdf2docx · img2pdf · Cloudflare R2 · Docker · bcrypt · slowapi (rate limiting)

---

## Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `DB_PATH` | No | `/data/zenvort.db` | SQLite database path (Docker volume `zenvort_data`) |
| `REDIS_URL` | Yes | `redis://redis:6379/0` | Redis for Celery broker/result backend |
| `PORT` | No | `3000` | API server port |
| `INTERNAL_SECRET` | Yes | — | Shared secret for internal API calls (`X-Internal-Secret`) |
| `R2_ACCOUNT_ID` | Yes | — | Cloudflare R2 account ID |
| `R2_ACCESS_KEY_ID` | Yes | — | R2 access key |
| `R2_SECRET_ACCESS_KEY` | Yes | — | R2 secret key |
| `R2_BUCKET_NAME` | Yes | — | R2 bucket name |
| `R2_PUBLIC_URL` | Yes | — | Public URL prefix (e.g. `https://xyz.r2.dev`) |
| `WORKER_CONCURRENCY` | No | `3` | Celery worker concurrency |
| `GOTENBERG_URL` | No | `http://gotenberg:3000` | Gotenberg service URL |
| `ADMIN_API_KEY` | Yes | — | API key of a Zenvort admin user |

---

## Getting Started

### 1. Prerequisites
- Docker Desktop
- Python 3.12+ (for local dev)
- Cloudflare R2 bucket with public access enabled

### 2. Environment Setup
```bash
cp .env.example .env
# Fill in all required variables in .env
```

### 3. Start Services
```bash
docker compose up --build
```

### 4. Create an Account
```bash
# Signup — returns your API key (save it!)
curl -X POST http://localhost:3000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"yourpassword"}'

# Login — returns your API key
curl -X POST http://localhost:3000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"yourpassword"}'
```

### 5. Check Supported Formats
```bash
# List all supported input formats
curl http://localhost:3000/formats

# List output options for a specific format
curl http://localhost:3000/formats/pdf
```

### 6. Submit a Conversion Job
```bash
curl -X POST http://localhost:3000/jobs \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F "file=@/path/to/document.pdf" \
  -F "outputFormat=docx"

# Poll job status
curl http://localhost:3000/jobs/JOB_ID \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## Database Schema

**Storage:** SQLite at `/data/zenvort.db` (via Docker volume `zenvort_data`)

```python
class User:
    id             # cuuid primary key
    email          # unique
    password       # bcrypt hash
    api_key        # raw API key (returned only at signup/login)
    api_key_hash   # SHA256 hash for lookup
    role           # "user" or "admin"
    webhook_url    # optional job status webhook
    created_at

class Job:
    id              # cuuid primary key
    user_id         # FK to User (nullable)
    status          # pending | processing | done | failed
    input_url       # R2 storage key (deleted immediately after conversion)
    output_url      # R2 storage key (deleted 20 min after DONE)
    input_format    # e.g. "pdf"
    output_format   # e.g. "docx"
    error           # sanitized error message (set on failure)
    converter_used  # masked as "zenvort-engine" in API response
    created_at
    updated_at
```

---

## API Routes

### `GET /health`
- **Auth:** None
- **Response:** `{ "ok": true, "timestamp": "..." }`

---

### `POST /auth/signup`
- **Auth:** None
- **Rate Limit:** 5000/hr
- **Body:** `{ "email": "...", "password": "..." }`
- **Response (201):**
```json
{
  "apiKey": "...",
  "user": { "id": "...", "email": "...", "role": "user", ... }
}
```

---

### `POST /auth/login`
- **Auth:** None
- **Rate Limit:** 30/15min
- **Body:** `{ "email": "...", "password": "..." }`
- **Response:**
```json
{
  "apiKey": "...",
  "user": { "id": "...", "email": "...", ... }
}
```

---

### `GET /formats`
- **Auth:** None
- **Response:**
```json
{
  "formats": ["avi", "avif", "bmp", ...],
  "total": 29
}
```

---

### `GET /formats/{fmt}`
- **Auth:** None
- **Response:**
```json
{
  "inputFormat": "pdf",
  "outputs": [
    { "format": "docx", "label": "DOCX" },
    { "format": "txt",  "label": "TXT"  },
    ...
  ]
}
```

---

### `POST /jobs`
- **Auth:** `Authorization: Bearer <apiKey>`
- **Body:** `multipart/form-data` with `file` (binary) and `outputFormat` (string)
- **Rate Limit:** 100 jobs/hour per user
- **Checks:** File present, outputFormat required, daily limit (50/day)
- **Process:**
  1. Extract extension as `inputFormat`
  2. Upload to R2 at `inputs/{jobId}/{filename}`
  3. Create Job in DB (status: pending)
  4. Dispatch Celery task `worker.tasks.process_job`
  5. Delete input from R2 immediately after conversion
  6. Schedule output deletion in 20 minutes
- **Response (201):** `{ "jobId": "...", "status": "PENDING", "message": "Job queued successfully" }`

---

### `GET /jobs`
- **Auth:** `Authorization: Bearer <apiKey>`
- **Query:** `page` (default 1), `limit` (default 20)
- **Rate Limit:** 100/min
- **Response:**
```json
{
  "jobs": [...],
  "total": 42,
  "page": 1,
  "limit": 20
}
```

---

### `GET /jobs/:id`
- **Auth:** `Authorization: Bearer <apiKey>`
- **Rate Limit:** 100/min
- **Response:** Full job object with signed download URLs (valid 20 minutes)
```json
{
  "id": "...",
  "status": "DONE",
  "inputUrl": null,
  "outputUrl": "https://...",
  "inputFormat": "pdf",
  "outputFormat": "docx",
  "error": null,
  "converterUsed": "zenvort-engine",
  "createdAt": "...",
  "updatedAt": "...",
  "expiresAt": "2026-05-08T04:00:00+00:00"
}
```
> **Note:** `outputUrl` is `null` once the 20-minute window expires. `expiresAt` is 20 minutes after `updatedAt`.

---

### `GET /user/me`
- **Auth:** `Authorization: Bearer <apiKey>`
- **Response:**
```json
{
  "id": "...",
  "email": "...",
  "role": "user",
  "webhookUrl": null,
  "createdAt": "...",
  "dailyUsage": 12,
  "dailyLimit": 50,
  "quotaResetAt": "2026-05-08T00:00:00+00:00"
}
```

---

### `PATCH /user/webhook`
- **Auth:** `Authorization: Bearer <apiKey>`
- **Body:** `{ "webhookUrl": "https://..." }`
- **Security:** Resolves hostname and rejects private/reserved IPs
- **Response:** `{ "ok": true, "webhookUrl": "..." }`

---

### Admin Routes (requires `role: admin`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/users` | Paginated user list |
| `GET` | `/admin/stats` | System-wide stats |

---

## Conversion Routes — 156 total

### Documents (28 input formats → multiple outputs)

| Input | Outputs | Library |
|-------|---------|---------|
| PDF | PNG, JPG, TXT, DOCX, HTML, RTF | Gotenberg + PyMuPDF + pdf2docx |
| DOCX | PDF, TXT, HTML, RTF | Gotenberg + Pandoc |
| MD | PDF, HTML, TXT, DOCX, RTF | Gotenberg + Pandoc |
| HTML | PDF, DOCX, TXT | Gotenberg |
| XLSX | PDF, HTML, CSV, TXT, DOCX | Gotenberg |
| PPTX | PDF, HTML, TXT, DOCX | Gotenberg |
| ODT | PDF, TXT, HTML, DOCX | Gotenberg |
| ODS | PDF, HTML, TXT | Gotenberg |
| ODP | PDF | Gotenberg |
| RTF | TXT, HTML, DOCX, PDF | Pandoc + Gotenberg |
| CSV | PDF, HTML, TXT, DOCX | Gotenberg |
| TXT | PDF, HTML, DOCX, RTF | Gotenberg |

### Images (8 input formats → 8 outputs + PDF)

| Input | Outputs | Library |
|-------|---------|---------|
| JPG, PNG, WebP, AVIF, BMP, TIFF, GIF | ↔ each other | Pillow |
| JPG, PNG, TIFF, BMP | PDF | img2pdf (lossless) |
| Other raster | PDF | Pillow → img2pdf |
| SVG | PNG, PDF | CairoSVG |

### Media (video/audio)

| Input | Outputs | Library |
|-------|---------|---------|
| MP4 | MP3, WebM, AVI, MOV, GIF, OGG, FLAC, WAV | FFmpeg |
| MP3 | WAV, OGG, FLAC, MP4, WebM | FFmpeg |
| WAV | MP3, OGG, FLAC, MP4, WebM | FFmpeg |
| WebM | MP4, MP3, AVI, MOV, OGG, FLAC, WAV | FFmpeg |
| AVI | MP4, MP3, WebM, MOV, OGG, FLAC, WAV, GIF | FFmpeg |
| MOV | MP4, MP3, WebM, AVI, OGG, FLAC, WAV, GIF | FFmpeg |
| OGG | MP3, WAV, FLAC, MP4, WebM | FFmpeg |
| FLAC | MP3, WAV, OGG, MP4, WebM | FFmpeg |

### OCR (images → text)

| Input | Output | Library |
|-------|--------|---------|
| JPG, PNG, WebP, BMP, TIFF, GIF, AVIF | TXT | Tesseract |

---

## File Retention

Files are automatically deleted to protect user privacy:

| File | Deletion |
|------|----------|
| **Input file** | Immediately after conversion (success or failure) |
| **Output file** | 20 minutes after job is marked done |
| **Presigned URL** | 20 minutes (expires before file deletion) |

A safety-net cleanup script (`worker/scripts/clear_stale_jobs.py`) runs as a cron fallback to delete any orphaned output files older than 20 minutes.

---

## Worker

**File:** `worker/tasks.py`

**Celery task:** `process_job(job_id)` — runs in the worker container

**Process:**
1. Update job status to `processing`
2. Download input from R2 to `/tmp/zenvort/{jobId}-input.{ext}`
3. Route to appropriate converter based on `worker/routes.py`
4. Validate output MIME type via `python-magic`
5. Upload output to R2 at `outputs/{jobId}/output.{ext}`
6. Update job to `done`
7. Delete input from R2 immediately
8. Schedule output deletion in 20 minutes via Celery `apply_async`
9. Send webhook (fire-and-forget, if configured)
10. Cleanup temp files

**Converters:** `worker/converters/`
- `documents.py` — Gotenberg + Pandoc + pdf2docx
- `images.py` — Pillow + PyMuPDF + img2pdf + CairoSVG
- `media.py` — FFmpeg
- `ocr.py` — Tesseract

**Retry policy:** 3 attempts with 30s backoff. Error messages are sanitized — no internal library names or file paths are exposed to users.

---

## Security

| Feature | Implementation |
|---------|---------------|
| **API Key Auth** | SHA256 hash lookup in DB, bcrypt for password |
| **Webhook SSRF** | Resolves hostname, rejects private/reserved IPs |
| **Path Traversal** | Temp files sandboxed to `/tmp/zenvort`, verified with `realpath` |
| **MIME Validation** | `python-magic` verifies output file matches expected type |
| **Error Sanitisation** | Internal library names, file paths, stack traces stripped before DB write |
| **File Retention** | Auto-delete inputs immediately, outputs after 20 minutes |
| **Daily Quota** | 50 conversions/day enforced server-side (429 on limit) |
| **Rate Limiting** | 100 job submits/hr, 100 reads/min, 30 logins/15min, 5000 signups/hr |

---

## File Structure

```
zenvort/
├── api/
│   ├── main.py              # FastAPI app, CORS, routers
│   ├── config.py            # Pydantic settings
│   ├── database.py          # Async SQLite engine + session
│   ├── schemas.py            # Pydantic request/response schemas
│   ├── deps.py               # get_current_user, get_admin_user
│   ├── storage.py            # R2 upload/download/delete/signed URL
│   ├── celery_client.py      # Celery app client (task dispatch)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── routes/
│       ├── auth.py           # POST /auth/signup, /auth/login
│       ├── jobs.py           # POST/GET /jobs, GET /jobs/:id
│       ├── user.py           # GET /user/me, PATCH /user/webhook
│       ├── formats.py        # GET /formats, GET /formats/{fmt}
│       └── admin.py          # Admin routes
├── worker/
│   ├── celery_app.py         # Celery app definition
│   ├── tasks.py              # process_job + delete_output_file tasks
│   ├── executor.py           # Routes conversion to correct converter
│   ├── routes.py             # 156 conversion routes
│   ├── storage.py            # R2 download/upload helpers
│   ├── config.py             # Worker settings
│   ├── utils.py              # Error sanitisation
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── converters/
│   │   ├── documents.py      # Gotenberg + Pandoc + pdf2docx
│   │   ├── images.py         # Pillow + PyMuPDF + img2pdf + CairoSVG
│   │   ├── media.py          # FFmpeg
│   │   ├── ocr.py            # Tesseract
│   │   └── calibre.py        # Calibre e-book conversion
│   ├── scripts/
│   │   └── clear_stale_jobs.py  # Safety-net cron cleanup
│   └── security/
│       ├── path_guard.py     # Path traversal prevention
│       └── mime_guard.py     # MIME type validation
├── migrations/
│   ├── 001_remove_bot.sql    # DB migration: drop bot tables
│   └── migrate-001-remove-bot.sh  # Cleanup script
├── docker-compose.yml
├── docker-compose.prod.yml
├── deploy.sh
├── .env.example
├── .env
└── SETUP.md
```

---

## Roadmap

```
✅ Phase 1 — Working Core (FastAPI + Celery)
✅ Phase 2 — 156 Conversion Routes
✅ Phase 3 — Security Hardening (SSRF, MIME, API key hashing)
✅ Phase 4 — API-only Backend (pure REST, no Telegram dependency)
✅ Phase 5 — File Retention (20-min auto-delete, expiry countdown)

🔜 Phase 6 — Growth & Monetisation
   [ ] Live Razorpay integration for billing/purchase
   [ ] Referral system
   [ ] Email notifications
   [ ] API docs / Swagger

🔜 Phase 7 — Enterprise & Scale
   [ ] Team accounts
   [ ] White-label option
   [ ] Priority queue
   [ ] Status page

🔜 Phase 8 — Advanced AI
   [ ] Batch jobs API
   [ ] Workflow builder
   [ ] Custom output quality settings
```