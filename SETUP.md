# Zenvort — Setup Guide

## Stack

- **API**: FastAPI (Python 3.12, aiosqlite, SQLite)
- **Worker**: Celery + Redis (file conversion via FFmpeg, Gotenberg, Pillow, PyMuPDF, Tesseract, Calibre, Pandoc)
- **Storage**: Cloudflare R2 (presigned URLs, auto-delete after 20 minutes)
- **Database**: SQLite at `/data/zenvort.db` (Docker volume `zenvort_data`)

---

## Docker Deployment (Quickstart)

```bash
# 1. Copy and fill in environment variables
cp .env.example .env
# Edit .env with your values (see Environment Variables below)

# 2. Build and start all services
docker compose up --build -d

# 3. Check logs
docker compose logs -f

# 4. Verify health
curl http://localhost:3000/health
```

The database (SQLite) is created automatically on first startup.

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `INTERNAL_SECRET` | Shared secret for internal API calls (`X-Internal-Secret`) |
| `R2_ACCOUNT_ID` | Cloudflare R2 account ID |
| `R2_ACCESS_KEY_ID` | R2 access key |
| `R2_SECRET_ACCESS_KEY` | R2 secret key |
| `R2_BUCKET_NAME` | R2 bucket name |
| `R2_PUBLIC_URL` | Public URL prefix (e.g. `https://xyz.r2.dev`) |
| `ADMIN_API_KEY` | API key of a Zenvort admin user |

---

## Generate INTERNAL_SECRET

```bash
openssl rand -hex 32
```

Paste the output as `INTERNAL_SECRET` in `.env`.

---

## Create an Admin User

```bash
# Signup via API
curl -X POST http://localhost:3000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@zenvort.bot","password":"yourpassword"}'

# Use the returned apiKey as ADMIN_API_KEY in .env
# Promote to admin in SQLite:
docker compose exec api sqlite3 /data/zenvort.db "UPDATE users SET role = 'admin' WHERE email = 'admin@zenvort.bot';"
```

---

## Cloudflare R2 Setup

1. Create an R2 bucket in your Cloudflare dashboard
2. Enable public access on the bucket (for presigned URL downloads)
3. Create an API token with R2 read/write permissions
4. Set `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_PUBLIC_URL` in `.env`

---

## Services

| Service | Port | Description |
|---------|------|-------------|
| `api` | 3000 | FastAPI REST API (exposed externally) |
| `worker` | — | Celery async job processor |
| `redis` | 6379 (internal) | Redis 7 for Celery |
| `gotenberg` | 3000 (internal) | Gotenberg/LibreOffice |

---

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | None | Health check |
| `/auth/signup` | POST | None | Create account |
| `/auth/login` | POST | None | Login |
| `/formats` | GET | None | List supported input formats |
| `/formats/{fmt}` | GET | None | List output options for a format |
| `/jobs` | POST | Bearer | Submit conversion job |
| `/jobs` | GET | Bearer | List user's jobs |
| `/jobs/{id}` | GET | Bearer | Get job status & download URL |
| `/user/me` | GET | Bearer | Current user profile + daily usage |
| `/user/webhook` | PATCH | Bearer | Set webhook URL for job completion |
| `/admin/users` | GET | Bearer + admin | List all users |
| `/admin/stats` | GET | Bearer + admin | System statistics |

---

## Troubleshooting

```bash
# Check all services are running
docker compose ps

# Tail logs for a specific service
docker compose logs -f api
docker compose logs -f worker

# Restart a single service
docker compose up -d --force-recreate worker

# Check SQLite database
docker compose exec api sqlite3 /data/zenvort.db ".tables"
```