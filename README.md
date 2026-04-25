# Zenvort

A CloudConvert-style file conversion SaaS built as a pnpm monorepo.

## What it does

Brief description: accepts file uploads via REST API, converts them using FFmpeg and LibreOffice, stores results on Cloudflare R2, and returns a download URL. Jobs are processed asynchronously via BullMQ.

## Architecture

Describe the monorepo structure:

- `apps/api` — Express REST API
- `apps/worker` — BullMQ job processor
- `packages/db` — Prisma + PostgreSQL
- `packages/queue` — BullMQ queue definitions
- `packages/storage` — Cloudflare R2 helpers

## Tech Stack

List: Node.js, TypeScript, Express, BullMQ, Redis, Prisma, PostgreSQL, Cloudflare R2, FFmpeg, LibreOffice, Docker, pnpm workspaces

## Getting Started

### Prerequisites

- Docker Desktop
- Node.js 20+
- pnpm
- Cloudflare R2 bucket with public access enabled

### Environment Setup

Copy .env.example to .env and fill in:

- DATABASE_URL
- REDIS_URL
- R2_ACCOUNT_ID
- R2_ACCESS_KEY_ID
- R2_SECRET_ACCESS_KEY
- R2_BUCKET_NAME
- R2_PUBLIC_URL

### Run locally

```bash
docker-compose up --build
```

### Run migrations

```bash
docker-compose run --rm migrate
```

### Seed test user

```bash
docker-compose run --rm seed
```

Test API key: `test-key-123`

## API Reference

### POST /jobs

Upload a file for conversion.

Headers: `Authorization: Bearer <apiKey>`

Body (multipart/form-data):

- `file`: the file to convert
- `outputFormat`: target format (e.g. pdf, docx, mp4)

Response: `{ jobId, status, message }`

### GET /jobs/:id

Poll job status.

Headers: `Authorization: Bearer <apiKey>`

Response: `{ id, status, inputFormat, outputFormat, inputUrl, outputUrl, error, createdAt }`

### GET /health

Returns API health status. No auth required.

## Supported Conversions

**Documents (via LibreOffice):** txt, docx, doc, pptx, xlsx, odt, html → pdf and between formats

**Video/Audio (via FFmpeg):** mp4, mov, avi, mkv, webm, mp3, wav, aac, flac → between formats

## Example Usage (PowerShell)

```powershell
# Health check
Invoke-RestMethod -Uri "http://localhost:3000/health"

# Submit job
$form = @{
    outputFormat = "pdf"
    file = Get-Item ".\test.txt"
}
Invoke-RestMethod -Uri "http://localhost:3000/jobs" `
    -Method POST `
    -Headers @{ Authorization = "Bearer test-key-123" } `
    -Form $form

# Poll job status (replace JOB_ID with actual id from response)
Invoke-RestMethod -Uri "http://localhost:3000/jobs/JOB_ID" `
    -Headers @{ Authorization = "Bearer test-key-123" }
```

## Roadmap

- [ ] Rate limiting per user
- [ ] Credit system + Stripe billing
- [ ] Webhook callbacks
- [ ] File TTL auto-deletion
- [ ] Worker autoscaling
- [ ] Web dashboard UI
- [ ] Self-hosted Docker image
- [ ] API SDKs (JavaScript, Python)
