# Zenvort

A CloudConvert-style file conversion SaaS. Accept file uploads via REST API, convert them using FFmpeg, Gotenberg, Pillow, Tesseract, and more, store results on Cloudflare R2, and return a download URL. Jobs are processed asynchronously via Celery + Redis.

---

## Architecture

```
                    ┌─────────────────┐
                    │   Browser /     │
                    │   Client App    │
                    └────────┬────────┘
                             │ HTTP
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                 api (FastAPI, :3000)                        │
│  /auth /jobs /user /billing /admin                          │
│  SQLAlchemy (async) ──▶ PostgreSQL                         │
│  Celery task dispatch ──▶ Redis                            │
└───────────────────────────────┬─────────────────────────────┘
                                │
              ┌─────────────────┴─────────────────┐
              ▼                                   ▼
┌─────────────────────────┐        ┌─────────────────────────┐
│  worker (Celery, Redis) │        │    Cloudflare R2         │
│  - FFmpeg (video/audio)│        │    inputs/{jobId}/       │
│  - Gotenberg (docs)    │        │    outputs/{jobId}/      │
│  - Pillow (images)     │        └─────────────────────────┘
│  - Tesseract (OCR)     │
│  - Calibre, Pandoc     │
└─────────────────────────┘
```

**Services:**
- `api` — FastAPI REST API (port 3000)
- `worker` — Celery async job processor
- `postgres` — PostgreSQL 16 (port 5432)
- `redis` — Redis 7 (port 6379)
- `gotenberg` — Gotenberg/LibreOffice (port 3002)

---

## Tech Stack

Python 3.12, FastAPI, SQLAlchemy (async), Alembic, PostgreSQL, Celery, Redis, Gotenberg (LibreOffice), FFmpeg, Pillow, Tesseract, Calibre, Pandoc, Cloudflare R2, Docker, bcrypt, slowapi (rate limiting)

---

## Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `DATABASE_URL` | Yes | — | PostgreSQL async connection (postgresql+asyncpg://...) |
| `DATABASE_URL_SYNC` | Yes | — | PostgreSQL sync connection (postgresql://...) |
| `REDIS_URL` | Yes | `redis://redis:6379/0` | Redis for Celery broker/result backend |
| `PORT` | No | `3000` | API server port |
| `R2_ACCOUNT_ID` | Yes | — | Cloudflare R2 account ID |
| `R2_ACCESS_KEY_ID` | Yes | — | R2 access key |
| `R2_SECRET_ACCESS_KEY` | Yes | — | R2 secret key |
| `R2_BUCKET_NAME` | Yes | — | R2 bucket name |
| `R2_PUBLIC_URL` | Yes | — | Public URL prefix (e.g. `https://xyz.r2.dev`) |
| `ALLOWED_ORIGIN` | No | `http://localhost:5173` | CORS allowed origin |
| `WORKER_CONCURRENCY` | No | `3` | Celery worker concurrency |
| `GOTENBERG_URL` | No | `http://gotenberg:3000` | Gotenberg service URL |

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
docker-compose up --build
```

### 4. Run Migrations
```bash
docker-compose run --rm migrate
```

### 5. Create an Account
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

**File:** `db/alembic/versions/` (Alembic migrations)

```python
class User:
    id           # cuuid primary key
    email        # unique
    password     # bcrypt hash (nullable for API-key-only auth)
    api_key      # raw API key (returned only at signup/login)
    api_key_hash # SHA256 hash for lookup
    credits      # default 100
    role         # "user" or "admin"
    webhook_url  # optional webhook for job status notifications
    created_at

class CreditLog:
    id        # cuuid primary key
    user_id   # FK to User
    amount    # positive = purchase, negative = deduction
    reason    # "signup" | "conversion" | "purchase" | "manual_add"
    job_id    # nullable, FK to Job
    created_at

class Job:
    id              # cuuid primary key
    user_id         # FK to User (nullable)
    status          # PENDING | PROCESSING | DONE | FAILED
    input_url       # R2 storage key
    output_url      # R2 storage key (set on completion)
    input_format    # e.g. "pdf"
    output_format   # e.g. "docx"
    error           # error message (set on failure)
    converter_used  # which converter succeeded
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
  "user": { "id": "...", "email": "...", "credits": 100, "role": "user", ... }
}
```

---

### `POST /auth/login`
- **Auth:** None
- **Rate Limit:** 5/15min
- **Body:** `{ "email": "...", "password": "..." }`
- **Response:**
```json
{
  "apiKey": "...",
  "user": { "id": "...", "email": "...", "credits": 100, ... }
}
```

---

### `POST /jobs`
- **Auth:** `Authorization: Bearer <apiKey>`
- **Body:** `multipart/form-data` with `file` (binary) and `outputFormat` (string)
- **Rate Limit:** 100 jobs/hour per user
- **Checks:** File present, outputFormat required, credits > 0 (402 if insufficient)
- **Process:**
  1. Extract extension as `inputFormat`
  2. Upload to R2 at `inputs/{jobId}/{filename}`
  3. Create Job in DB (status: PENDING)
  4. Dispatch Celery task `worker.tasks.process_job`
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
- **Response:** Full job object with signed download URLs
```json
{
  "id": "...",
  "status": "DONE",
  "inputUrl": "...",
  "outputUrl": "...",
  "inputFormat": "pdf",
  "outputFormat": "docx",
  "error": null,
  "converterUsed": "zenvort-engine",
  "createdAt": "...",
  "updatedAt": "..."
}
```

---

### `GET /user/me`
- **Auth:** `Authorization: Bearer <apiKey>`
- **Response:** `{ "id": "...", "email": "...", "credits": 99, "role": "user", ... }`

---

### `PATCH /user/webhook`
- **Auth:** `Authorization: Bearer <apiKey>`
- **Body:** `{ "webhookUrl": "https://..." }`
- **Security:** Resolves hostname and rejects private/reserved IPs
- **Response:** `{ "ok": true, "webhookUrl": "..." }`

---

### `GET /billing/plans`
- **Auth:** None
- **Response:**
```json
[
  { "pack": "starter", "credits": 500, "amount": 199, "currency": "INR", "name": "Starter Pack" },
  { "pack": "pro", "credits": 2000, "amount": 599, "currency": "INR", "name": "Pro Pack" },
  { "pack": "enterprise", "credits": 10000, "amount": 1999, "currency": "INR", "name": "Enterprise Pack" }
]
```

---

### `POST /billing/purchase`
- **Auth:** `Authorization: Bearer <apiKey>`
- **Rate Limit:** 5/min
- **Body:** `{ "pack": "starter" | "pro" | "enterprise" }`
- **Status:** Stub — returns `"Payment integration coming soon"`
- **Response:** `{ "ok": true, "message": "Payment integration coming soon" }`

---

### `GET /billing/usage`
- **Auth:** `Authorization: Bearer <apiKey>`
- **Rate Limit:** 30/min
- **Response:**
```json
{
  "credits": 99,
  "totalJobs": 42,
  "jobsToday": 3,
  "successRate": 97.62,
  "dailyUsage": [{ "date": "2026-04-26", "count": 5 }, ...]
}
```

---

### `GET /billing/transactions`
- **Auth:** `Authorization: Bearer <apiKey>`
- **Response:**
```json
{
  "logs": [
    { "id": "...", "amount": -1, "reason": "conversion", "jobId": "...", "createdAt": "..." },
    { "id": "...", "amount": 100, "reason": "signup", "createdAt": "..." }
  ]
}
```

---

### Admin Routes (requires `role: admin`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/users` | Paginated user list |
| `GET` | `/admin/stats` | System-wide stats |
| `PATCH` | `/admin/users/{id}/credits` | Add/subtract credits |

---

## Conversion Routes (145 total)

### Document → Document / PDF / Image
Supported via **Gotenberg** (LibreOffice): PDF, DOCX, MD, HTML, XLSX, PPTX, ODT, ODS, ODP, RTF, CSV, TXT

### Image → Image / PDF
Supported via **Pillow**: JPG, PNG, WebP, AVIF, BMP, TIFF, GIF ↔ each other + PDF

### Video / Audio
Supported via **FFmpeg**: MP4, WebM, AVI, MOV, MP3, WAV, OGG, FLAC ↔ each other + GIF

### OCR (Image → TXT)
Supported via **Tesseract**: JPG, PNG, WebP, BMP, TIFF, GIF, AVIF → TXT

### Document Conversion
- **RTF** → TXT/HTML/DOCX/PDF via **Pandoc**
- **EPUB** → various via **Calibre**
- **MD** ↔ DOCX/HTML/PDF via **Gotenberg**

---

## Worker

**File:** `worker/tasks.py`

**Celery task:** `process_job(job_id)`

**Process:**
1. Update job status to `PROCESSING`
2. Download input from R2 to `/tmp/zenvort/{jobId}-input.{inputFormat}`
3. Route to appropriate converter (FFmpeg / Gotenberg / Pillow / Tesseract / Calibre / Pandoc)
4. Validate output MIME type matches expected format
5. Upload output to R2 at `outputs/{jobId}/output.{outputFormat}`
6. Update job to `DONE`, set `outputUrl`, deduct 1 credit, log to CreditLog
7. Send webhook (fire-and-forget, if configured)
8. Cleanup temp files

**Retry policy:** 3 attempts with 30s exponential backoff

**Webhook payload (on DONE/FAILED):**
```json
{
  "jobId": "...",
  "status": "DONE" | "FAILED",
  "outputUrl": "https://...",
  "error": "..." | null,
  "timestamp": "..."
}
```

---

## Security

| Feature | Implementation |
|---------|---------------|
| **API Key Auth** | SHA256 hash lookup in DB, bcrypt for password |
| **Webhook SSRF** | Resolves hostname, rejects private/reserved IPs |
| **Path Traversal** | Temp files sandboxed to `/tmp/zenvort` |
| **MIME Validation** | `python-magic` verifies output file matches expected type |
| **Credit Floor** | DB-level `CHECK (credits >= 0)` constraint |
| **Double Deduction** | Unique partial index on `credit_logs(job_id)` where reason='conversion' |
| **Rate Limiting** | 100 job submits/hr, 100 reads/min, 5 logins/15min, 5000 signups/hr |

---

## File Structure

```
zenvort/
├── api/
│   ├── main.py              # FastAPI app entry, CORS, routers
│   ├── config.py            # Settings (pydantic)
│   ├── database.py          # Async SQLAlchemy engine + session
│   ├── models.py            # User, Job, CreditLog SQLAlchemy models
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── deps.py              # get_current_user, get_admin_user
│   ├── storage.py           # R2 upload/download/delete/signed URL
│   ├── celery_client.py     # Celery app client (for dispatching tasks)
│   ├── requirements.txt
│   ├── Dockerfile           # FastAPI image
│   └── routes/
│       ├── auth.py          # POST /auth/signup, /auth/login
│       ├── jobs.py          # POST/GET /jobs, GET /jobs/:id
│       ├── user.py          # GET /user/me, PATCH /user/webhook
│       ├── billing.py       # GET /billing/plans, POST/GET /billing/*
│       └── admin.py         # GET /admin/users, /admin/stats, PATCH credits
├── worker/
│   ├── celery_app.py        # Celery app definition
│   ├── tasks.py             # process_job Celery task
│   ├── executor.py          # Routes conversion to correct converter
│   ├── routes.py            # 145 conversion routes + format lists
│   ├── storage.py           # R2 download/upload helpers
│   ├── config.py            # Worker settings
│   ├── requirements.txt
│   ├── Dockerfile           # Worker image (includes ffmpeg, tesseract, etc.)
│   ├── converters/
│   │   ├── gotenberg.py     # LibreOffice via Gotenberg
│   │   ├── ffmpeg.py        # FFmpeg wrappers
│   │   ├── pillow.py        # Pillow image processing
│   │   ├── tesseract.py     # Tesseract OCR
│   │   ├── calibre.py       # Calibre e-book conversion
│   │   └── pandoc.py        # Pandoc document conversion
│   └── security/
│       ├── path_guard.py    # Path traversal prevention
│       └── mime_guard.py    # MIME type validation
├── db/
│   └── alembic/
│       ├── env.py
│       └── versions/
│           ├── 001_initial.py
│           ├── 002_strip_r2_urls.py
│           └── 003_credit_floor.py
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
└── .env
```

---

## Roadmap

```
✅ Phase 1 — Working Core (FastAPI + Celery)
✅ Phase 2 — 145 Conversion Routes
✅ Phase 3 — Security Hardening (SSRF, MIME, credit floor, API key hashing)

🔜 Phase 4 — SaaS Web Dashboard
   [ ] Landing page with pricing
   [ ] User signup / login
   [ ] Dashboard with job upload + history
   [ ] API key management UI
   [ ] Credit balance display
   [ ] Admin panel

🔜 Phase 5 — Growth & Monetisation
   [ ] Live Razorpay integration for billing/purchase
   [ ] Email notifications
   [ ] Referral system
   [ ] Swagger / OpenAPI docs

🔜 Phase 6 — Enterprise & Scale
   [ ] Team accounts
   [ ] White-label option
   [ ] Priority queue
   [ ] Status page

🔜 Phase 7 — AI Features
   [ ] Whisper transcription
   [ ] Tesseract OCR (already available!)
   [ ] Batch jobs API
   [ ] Workflow builder
```
