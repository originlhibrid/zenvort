# ZENVORT — Full Project Context

## What is Zenvort
A file conversion SaaS API. Users upload files → backend queues
conversion job (converter chain with fallbacks) → user polls or gets webhook
when done. Credit-based system (1 credit per conversion).
Beta: no payment integration, credits granted manually.

---

## Architecture

```
                    ┌─────────────────┐
                    │   Browser /     │
                    │   Frontend      │
                    │ (localhost:5173)│
                    └────────┬────────┘
                             │ HTTP
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                    api (FastAPI, :3000)                      │
│  /auth/*, /jobs, /user, /billing, /admin                    │
│  CORS: allowlist only (no wildcard)                          │
│  slowapi rate limiting (signup/login/job submit)             │
└─────────────────────────────┬────────────────────────────────┘
                              │ SQLAlchemy async
                              ▼
              ┌───────────────┐
              │  PostgreSQL   │
              │   Port 5432   │
              │  (user: zenvort)
              └───────────────┘

              ┌───────────────┐         ┌───────────────┐
              │    Redis      │         │ Cloudflare R2 │
              │   Port 6379   │         │  (Storage)    │
              └───────────────┘         └───────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              worker (Celery, Redis broker)                  │
│  - Gotenberg for document/PDF conversions (HTTP API)       │
│  - FFmpeg for video/audio (subprocess)                     │
│  - Pillow for image-to-image (replaces Sharp)              │
│  - Job caching (re-use DONE outputs for identical inputs)  │
│  - Semaphore: max WORKER_CONCURRENCY concurrent            │
│  - Disk space guard: 2GB /tmp/zenvort/ limit              │
│  - Webhook sender (httpx, fire-and-forget)                 │
└─────────────────────────────────────────────────────────────┘

              ┌───────────────┐
              │   Gotenberg   │
              │   Port 3002   │
              │ (libreoffice  │
              │  + chromium)  │
              └───────────────┘
```

---

## Tech Stack
Python 3.12, FastAPI, Celery 5, SQLAlchemy 2.0 (async), Alembic,
Redis, PostgreSQL, boto3 (Cloudflare R2), FFmpeg, Gotenberg v8,
Pillow, python-magic, slowapi, Docker.

Frontend (UNCHANGED): **Vite + React 19 + Tailwind CSS v3 + shadcn/ui + React Router v7**

---

## Getting Started

```bash
# Copy and fill in env
cp .env.example .env

# Start all services
docker compose up --build -d

# Run Alembic migrations
docker compose run --rm migrate alembic upgrade head

# Check API health
curl http://localhost:3000/health

# Open frontend (Vite dev server)
cd zenvort-dashboard
npm run dev  # http://localhost:5173
```

---

## Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://...` | Async PostgreSQL URL (SQLAlchemy async) |
| `DATABASE_URL_SYNC` | Yes | `postgresql://...` | Sync PostgreSQL URL (Alembic + Celery worker) |
| `REDIS_URL` | Yes | `redis://redis:6379/0` | Redis for Celery broker + backend |
| `PORT` | No | `3000` | API server port |
| `R2_ACCOUNT_ID` | Yes | — | Cloudflare R2 account ID |
| `R2_ACCESS_KEY_ID` | Yes | — | R2 access key |
| `R2_SECRET_ACCESS_KEY` | Yes | — | R2 secret key |
| `R2_BUCKET_NAME` | Yes | — | R2 bucket name |
| `R2_PUBLIC_URL` | Yes | — | Public URL prefix (e.g. `https://xyz.r2.dev`) |
| `ALLOWED_ORIGIN` | No | `http://localhost:5173` | CORS allowlist (frontend URL) |
| `WORKER_CONCURRENCY` | No | `3` | Celery worker concurrency (semaphore limit) |
| `GOTENBERG_URL` | No | `http://gotenberg:3002` | Gotenberg service URL |

---

## Project Structure

```
zenvort/
├── docker-compose.yml          -- postgres, redis, gotenberg, api, worker, migrate
├── .env / .env.example
│
├── api/                        -- FastAPI (async)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── config.py               -- pydantic-settings
│   ├── database.py             -- SQLAlchemy async engine + get_db()
│   ├── models.py               -- User, CreditLog, Job (SQLAlchemy 2.0)
│   ├── schemas.py              -- Pydantic models (camelCase aliases)
│   ├── deps.py                 -- get_current_user(), get_admin_user()
│   ├── storage.py              -- boto3 R2 helpers (upload/download/delete)
│   ├── main.py                 -- FastAPI app, CORS, rate limiter, /health
│   └── routes/
│       ├── auth.py             -- POST /auth/signup, POST /auth/login
│       ├── jobs.py              -- GET /jobs, POST /jobs, GET /jobs/:id
│       ├── user.py              -- GET /user/me, PATCH /user/webhook
│       ├── billing.py           -- GET /billing/plans, /usage, /transactions, POST /purchase
│       └── admin.py            -- GET /admin/users, /admin/stats, PATCH /admin/users/:id/credits
│
├── worker/                     -- Celery worker (sync)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── config.py               -- pydantic-settings
│   ├── celery_app.py           -- Celery app (broker + backend = Redis)
│   ├── tasks.py                -- process_job() Celery task
│   ├── executor.py             -- execute_conversion() fallback chain
│   ├── routes.py               -- ROUTES dict + VALID_INPUT/OUTPUT_FORMATS
│   ├── storage.py              -- boto3 R2 helpers (shared with api)
│   ├── converters/
│   │   ├── gotenberg.py       -- HTTP to Gotenberg /forms/libreoffice/convert
│   │   ├── ffmpeg.py           -- subprocess.run() FFmpeg (no shell=True)
│   │   └── pillow.py           -- Pillow image-to-image (replaces Sharp)
│   ├── security/
│   │   ├── path_guard.py      -- sanitize_and_assert_tmp_path()
│   │   └── mime_guard.py       -- assert_mime_type_matches() via python-magic
│   └── scripts/
│       └── clear_stale_jobs.py -- drain stale Celery tasks + mark DB rows FAILED
│
├── db/                         -- Shared models + Alembic migrations
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
│       └── 001_initial.py     -- all tables + indexes (sync migration)
│
└── zenvort-dashboard/         -- UNTOUCHED (React frontend)
```

---

## Database Schema

**File:** `api/models.py` (SQLAlchemy 2.0) + `db/alembic/versions/001_initial.py`

All column names are **snake_case** in the database. JSON responses use
**camelCase** via Pydantic `alias_generator=to_camel` on every schema.

**Auth improvement:** API keys are hashed with SHA-256 before storage
(`api_key_hash` column). The raw key is returned only at signup/login.

```python
# User
id          String PK (uuid4)
email       String UNIQUE (indexed)
password    String (bcrypt hashed, nullable)
api_key     String UNIQUE (returned only at signup/login)
api_key_hash String UNIQUE (SHA-256 of raw key, used for auth queries)
credits     Integer default 100
role        String default "user"  -- "user" | "admin"
webhook_url String nullable
created_at  DateTime default now()

# CreditLog
id         String PK (uuid4)
user_id    String FK → users.id
amount     Integer
reason     String  -- 'signup'|'conversion'|'purchase'|'manual_add'|'manual_deduct'
job_id     String nullable
created_at DateTime default now()
INDEX: (user_id), (user_id, created_at)

# Job
id             String PK (uuid4)
user_id        String nullable FK → users.id
status         String default "PENDING"  -- PENDING|PROCESSING|DONE|FAILED
input_url      String
output_url     String nullable
input_format   String
output_format  String
error          String nullable
converter_used  String nullable  -- which converter succeeded
created_at     DateTime default now()
updated_at     DateTime onupdate=now()
INDEX: (user_id), (status), (user_id, created_at), (input_url, output_format, status)
```

---

## Converter Routing Table

**Source of truth:** `worker/routes.py` (`ROUTES` dict)

Gotenberg handles all document conversions via HTTP. FFmpeg handles all
video/audio. Pillow handles image-to-image only (jpg/png/webp/avif).

All routes:
- **PDF:** png, jpg, txt, docx, html, pdf-optimize (Gotenberg)
- **DOCX:** pdf, txt, html (Gotenberg)
- **MD:** pdf, html, txt, docx (Gotenberg)
- **HTML:** pdf, docx (Gotenberg)
- **Images:** jpg↔png, jpg↔webp, jpg↔avif, png↔jpg, png↔webp, png↔avif, webp↔jpg, webp↔png, jpg→pdf, png→pdf (Pillow + Gotenberg)
- **Video/Audio:** mp4→mp3, mp4→webm, mp3→wav, wav→mp3 (FFmpeg)

Gotenberg endpoints:
- `/forms/libreoffice/convert` — all document conversions
- `/forms/pdfengines/convert` — image→PDF (uses Chromium for higher fidelity)

---

## process_job Flow (worker/tasks.py)

```
1.  Mark job PROCESSING in DB
2.  Guard: inputFormat == outputFormat → FAILED, unrecoverable, no retry
3.  Log: [worker][jobId] Job received {inputFormat, outputFormat, userId}
4.  Disk space check: if /tmp/zenvort/ free < 2GB → self.retry() (retryable)
5.  Semaphore acquire() — block if at WORKER_CONCURRENCY limit
6.  Download from R2:
    - Extract filename from inputUrl URL path segment
    - Fall back to inputFormat if URL has no extension
    - inputPath = /tmp/zenvort/{jobId}-input.{ext}
7.  Input file size check: > 200MB → mark FAILED (unrecoverable), cleanup
8.  Cache lookup: find prior DONE job with same inputUrl + outputFormat
    → if hit: mark DONE with cached outputUrl, fire webhook, return (no credit deducted)
9.  Log: [worker][jobId] Conversion started
10. execute_conversion() — sequential fallback chain via get_route()
11. Log: [worker][jobId] Conversion done {converterUsed}
12. Output file size check: > 500MB → mark FAILED (unrecoverable), cleanup
13. assert_mime_type_matches() via python-magic
14. Upload output to R2 at outputs/{jobId}/output.{outputFormat}
15. Mark job DONE with outputUrl + converterUsed
16. Deduct 1 credit + CreditLog(reason='conversion')
17. Fire webhook httpx POST (fire-and-forget)
18. On retryable error: mark FAILED, self.retry(exc=exc, countdown=30)
19. On SoftTimeLimitExceeded: mark FAILED, no retry
20. On unrecoverable error: mark FAILED, no retry
21. finally: semaphore.release() + _cleanup(jobId) deletes all /tmp/zenvort/{jobId}-* files
```

---

## API Routes

### Auth

#### POST /auth/signup
- **Auth:** None
- **Body:** `{ email: str, password: str }` (pydantic ValidationError on bad input)
- **Rate limit:** 5/hour per IP (slowapi)
- **Process:** bcrypt hash, generate `secrets.token_urlsafe(32)` as raw apiKey,
  SHA-256 hash stored in `api_key_hash`, create User with 100 credits,
  CreditLog(reason='signup')
- **Response 201:** `{ apiKey: str, user: { id, email, credits, role } }`
- **Error 409:** email already registered

#### POST /auth/login
- **Auth:** None
- **Body:** `{ email: str, password: str }`
- **Rate limit:** 5/15min per IP (slowapi)
- **Process:** bcrypt verify, return raw apiKey
- **Response 200:** `{ apiKey: str, user: { id, email, credits, role, webhookUrl } }`
- **Error 401:** invalid credentials

### User

#### GET /user/me
- **Auth:** `Authorization: Bearer <apiKey>`
- **Response:** `{ id, email, credits, webhookUrl, role, createdAt }`

#### PATCH /user/webhook
- **Auth:** `Authorization: Bearer <apiKey>`
- **Body:** `{ webhookUrl: str }` — regex validated
- **Response:** `{ ok: true, webhookUrl: str }`

### Jobs

#### GET /jobs
- **Auth:** `Authorization: Bearer <apiKey>`
- **Query:** `?page=1&limit=20`
- **Response:** `{ jobs: [...], total, page, limit }`

#### POST /jobs
- **Auth:** `Authorization: Bearer <apiKey>`
- **Body:** multipart/form-data — `file` (binary) + `outputFormat` (string)
- **Rate limit:** 10/hour per user_id (slowapi, keyed on user from Bearer token)
- **File size limit:** 100MB (413 if exceeded)
- **Checks:** file present, credits > 0 (402 if insufficient),
  outputFormat in VALID_OUTPUT_FORMATS, inputFormat in VALID_INPUT_FORMATS
- **Input format:** inferred from filename extension (sanitized)
- **Process:** upload to R2 `inputs/{jobId}/{safeName}`, create Job(PENDING),
  `process_job.delay(jobId)` via Celery
- **Response 201:** `{ jobId: str, status: "PENDING", message: str }`

#### GET /jobs/:id
- **Auth:** `Authorization: Bearer <apiKey>`
- **IDOR protection:** 403 if job.user_id != current user
- **Response:** full Job schema

### Billing

#### GET /billing/plans
- **Auth:** None
- **Response:** `[{ pack, credits, amount, currency, name }]` — hardcoded

#### GET /billing/usage
- **Auth:** `Authorization: Bearer <apiKey>`
- **Response:** `{ credits, totalJobs, jobsToday, successRate, dailyUsage }`

#### GET /billing/transactions
- **Auth:** `Authorization: Bearer <apiKey>`
- **Response:** `{ logs: [{ id, amount, reason, jobId, createdAt }] }`

#### POST /billing/purchase
- **Auth:** `Authorization: Bearer <apiKey>`
- **Stub:** `{ ok: true, message: "Payment integration coming soon" }`

### Admin (role=admin only, 403 otherwise)

#### GET /admin/users
- **Query:** `?page=1&limit=20`
- **Response:** `{ users: [...], total, page, limit }`

#### GET /admin/stats
- **Response:** `{ totalUsers, totalJobs, totalCredits, jobsByStatus }`

#### PATCH /admin/users/:id/credits
- **Body:** `{ amount: int, reason: str }`
- **Process:** update user credits, CreditLog entry
- **Response:** `{ ok: true, credits: int }`

### Health

#### GET /health
- **Auth:** None
- **Response:** `{ ok: true, timestamp: "..." }`

---

## Auth System
- All requests: `Authorization: Bearer <apiKey>`
- Raw API key stored in DB (`api_key` column), returned at signup/login only
- SHA-256 hash in `api_key_hash` column used for DB lookups
- Passwords: bcrypt (cost factor 4.2.0 default ~12)
- Roles: "user" (default) or "admin"
- No JWT — stateless API key auth only

---

## Security

**CORS:** `api/main.py` — allowlist from `ALLOWED_ORIGIN`, no wildcard

**Auth:** SHA-256 hashed API keys in DB, raw key returned at signup/login only

**Format validation:** `worker/routes.py` — `VALID_INPUT_FORMATS` and `VALID_OUTPUT_FORMATS` derived from `ROUTES` dict, imported by `api/routes/jobs.py`

**Path traversal protection:**
- Worker: `sanitize_and_assert_tmp_path()` — all paths must resolve under `/tmp/zenvort/`
- API: filename sanitized via `re.sub(r"[^a-zA-Z0-9_\.\-]", "_", filename)`

**Worker file bounds:** `/tmp/zenvort/` — dedicated subdirectory, not bare `/tmp/`

**Rate limiting:** slowapi (Starlette middleware)
- Signup: 5/hour per IP
- Login: 5/15min per IP
- Job submit: 10/hour per user_id (from Bearer token, not raw IP)

**File size limits:**
- API upload: 100MB (413 if exceeded)
- Worker input: 200MB (unrecoverable FAILED if exceeded)
- Worker output: 500MB (unrecoverable FAILED if exceeded)

**IDOR protection:** GET /jobs/:id checks `job.user_id == current_user.id`

**No shell=True:** All subprocess calls use `subprocess.run()` with argument lists only

**MIME validation:** `worker/security/mime_guard.py` via `python-magic`

---

## Docker Services

```
postgres   postgres:16-alpine   :5432  (healthcheck)
redis      redis:7-alpine       :6379
gotenberg  gotenberg/gotenberg:8 :3002  (--chromium-disable-routes=false, --libreoffice-restart-after=10)
api        ./api/Dockerfile     :3000
worker     ./worker/Dockerfile  (Celery worker, no published port)
migrate    ./api/Dockerfile     (alembic upgrade head, restart: no)
```

### Migrate command
```bash
docker compose run --rm migrate alembic upgrade head
```

---

## Frontend (zenvort-dashboard/) — UNTOUCHED

**Stack:** Vite + React 19 + React Router v7 + Tailwind CSS v3 + shadcn/ui + Lucide React

**Dev server:** `npm run dev` → http://localhost:5173

**Routes:**
- `/` — Landing page (public)
- `/login` — Email/password login
- `/signup` — Email/password signup
- `/dashboard` — Stats + upload form + job list
- `/api-key` — API key display + copy (protected)
- `/billing` — Credit balance + plan selection
- `/admin` — User table + platform stats (admin only)

**Auth storage:** `zenvort_api_key` (localStorage), `zenvort_user` (localStorage)

---

## Testing

```bash
# Health check
curl http://localhost:3000/health

# Sign up
curl -X POST http://localhost:3000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Login
curl -X POST http://localhost:3000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Use returned apiKey for authenticated requests
curl http://localhost:3000/user/me \
  -H "Authorization: Bearer <apiKey>"
```

---

## Known Issues (RESOLVED)

- **OLD: LibreOffice exit code 1 with valid output** → Fixed in Node.js worker via
  stat check in libreoffice.ts — Python version uses Gotenberg instead (no LocalOffice)
- **OLD: No path traversal protection in worker** → Fixed: `sanitize_and_assert_tmp_path()`
  rejects all paths outside `/tmp/zenvort/`
- **OLD: Shell injection in converter commands** → Fixed: `subprocess.run()` with argument
  lists only, no shell=True; Gotenberg calls use httpx (no shell)
- **OLD: Worker at max concurrency without conversion-level enforcement** → Fixed:
  `threading.Semaphore(WORKER_CONCURRENCY)` in `worker/tasks.py`
- **OLD: No disk space guard** → Fixed: `os.disk_usage()` check before conversion
- **OLD: Converter outputting wrong MIME type silently** → Fixed:
  `assert_mime_type_matches()` via `python-magic` before R2 upload
- **OLD: Job submit rate limiter keyed on raw IP** → Fixed: slowapi `get_user_id_for_limit`
  extracts user from Bearer token for POST /jobs rate limit
- **OLD: No job result caching** → Fixed: cache lookup by (input_url, output_format, status=DONE)
  before conversion
- **OLD: RedisConnection imported as default in queue** → Fixed: N/A (Celery uses direct URL)
- **OLD: Shared package missing from Dockerfile build** → Fixed: both Dockerfiles `COPY api/ ./api/` and `COPY worker/ ./worker/` include their own code

---

## Remaining Work

- [ ] Alembic migration for `api_key_hash` (add column, backfill, add constraint)
- [ ] Upgrade bcrypt cost factor to 12
- [ ] Live Razorpay integration (credit purchase flow)
- [ ] Email verification on signup
- [ ] Password reset flow
- [ ] Swagger API docs
- [ ] Team accounts (Phase 6)
- [ ] White-label option (Phase 6)
- [ ] Priority queue (Phase 6)
- [ ] Status page (Phase 6)
- [ ] Whisper transcription (Phase 7)
- [ ] Tesseract OCR (Phase 7)
- [ ] Batch jobs API (Phase 7)
- [ ] Workflow builder (Phase 7)
- [ ] Chrome extension (Phase 8)
- [ ] Zapier integration (Phase 8)
- [ ] Mobile app (Phase 8)

---

## Roadmap

```
✅ Phase 1 — Working Core (Node.js/BullMQ/Prisma)
✅ Phase 2 — Make it Usable
✅ Phase 3 — Production Ready
✅ Phase 4 — SaaS Web Dashboard (Vite + React + shadcn/ui + Tailwind v3)
✅ Phase 5 — Growth & Monetisation (partial: billing routes exist, Razorpay not live)
✅ FIXED — Frontend wiring to real API
✅ FIXED — All critical security issues (IDOR, CORS, rate limiting, path traversal, file size, shell injection)
✅ FIXED — Worker reliability (timeouts, lockDuration, DB indexes)
✅ FIXED — Converter routing table with fallback chains
✅ FIXED — Worker metrics + orphan cleanup
✅ FIXED — Job result caching
✅ FIXED — MIME type validation before R2 upload
✅ FIXED — Disk space guard + concurrency semaphore
✅ FIXED — LibreOffice mutex + per-job profile
✅ MIGRATED — Backend migrated from Node.js/TypeScript to Python/FastAPI/Celery
✅ MIGRATED — Gotenberg replaces LibreOffice/Pandoc/Sharp/ImageMagick/Ghostscript
✅ MIGRATED — Prisma+PostgreSQL → SQLAlchemy 2.0 async + Alembic
✅ MIGRATED — BullMQ → Celery 5 (Redis broker)

🔜 Phase 5 (continued)
   [ ] Alembic migration for api_key_hash column
   [ ] Live Razorpay integration
   [ ] Credit purchase flow
   [ ] Email notifications
   [ ] Referral system
   [ ] Swagger docs

🔜 Phase 6 — Enterprise & Scale
   [ ] Team accounts
   [ ] White-label option
   [ ] Priority queue
   [ ] Status page

🔜 Phase 7 — AI Features
   [ ] Whisper transcription
   [ ] Tesseract OCR
   [ ] Batch jobs API
   [ ] Workflow builder

🔜 Phase 8 — Distribution
   [ ] Chrome extension
   [ ] Zapier integration
   [ ] Mobile app
```
