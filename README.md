# Zenvort

A CloudConvert-style file conversion SaaS built as a pnpm monorepo. Accepts file uploads via REST API, converts them using FFmpeg and LibreOffice, stores results on Cloudflare R2, and returns a download URL. Jobs are processed asynchronously via BullMQ.

---

## Architecture

```
                    ┌─────────────────┐
                    │   Browser /     │
                    │   Frontend      │
                    │(zenvort-dashboard)│
                    └────────┬────────┘
                             │ HTTP
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                     apps/api (Express, :3000)                │
│  /jobs, /user, /billing  ───▶  Prisma  ───▶  PostgreSQL     │
│                               Redis (rate limiting)          │
│                               BullMQ  ───▶  Redis           │
└───────────────────────────────┼─────────────────────────────┘
                                │
              ┌─────────────────┴─────────────────┐
              ▼                                   ▼
┌─────────────────────────┐        ┌─────────────────────────┐
│  apps/worker (BullMQ)   │        │    Cloudflare R2         │
│  - FFmpeg (video/audio) │        │    inputs/{jobId}/       │
│  - LibreOffice (docs)   │        │    outputs/{jobId}/      │
│  - Webhook sender       │        └─────────────────────────┘
└─────────────────────────┘
```

**Services:**
- `apps/api` — Express REST API (ports: 3000)
- `apps/worker` — BullMQ job processor
- `packages/db` — Prisma + PostgreSQL
- `packages/queue` — BullMQ queue definitions
- `packages/storage` — Cloudflare R2 helpers

---

## Tech Stack

Node.js, TypeScript, Express, BullMQ, Redis, Prisma, PostgreSQL, Cloudflare R2, FFmpeg, LibreOffice, Docker, pnpm workspaces, Razorpay

---

## Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `REDIS_URL` | Yes | `redis://redis:6379` | Redis for BullMQ + rate limiting |
| `PORT` | No | `3000` | API server port |
| `R2_ACCOUNT_ID` | Yes | — | Cloudflare R2 account ID |
| `R2_ACCESS_KEY_ID` | Yes | — | R2 access key |
| `R2_SECRET_ACCESS_KEY` | Yes | — | R2 secret key |
| `R2_BUCKET_NAME` | Yes | — | R2 bucket name |
| `R2_PUBLIC_URL` | Yes | — | Public URL prefix (e.g. `https://xyz.r2.dev`) |
| `RAZORPAY_KEY_ID` | For billing | — | Razorpay API key |
| `RAZORPAY_KEY_SECRET` | For billing | — | Razorpay secret |
| `WORKER_CONCURRENCY` | No | `3` | BullMQ worker concurrency |

---

## Getting Started

### 1. Prerequisites
- Docker Desktop
- Node.js 20+
- pnpm
- Cloudflare R2 bucket with public access enabled

### 2. Environment Setup
```bash
cp .env.example .env
# Fill in all variables in .env
```

### 3. Start Services
```bash
docker-compose up --build
```

### 4. Run Migrations
```bash
docker-compose run --rm migrate
```

### 5. Seed Test User
```bash
docker-compose run --rm seed
```

Test user: `test@zenvort.com` / API key: `test-key-123`

### Test It
```bash
# Health check
curl http://localhost:3000/health

# Submit a job (PowerShell)
$form = @{ outputFormat = "pdf"; file = Get-Item ".\test.txt" }
Invoke-RestMethod -Uri "http://localhost:3000/jobs" -Method POST `
  -Headers @{ Authorization = "Bearer test-key-123" } -Form $form

# Poll job status
Invoke-RestMethod -Uri "http://localhost:3000/jobs/JOB_ID" `
  -Headers @{ Authorization = "Bearer test-key-123" }
```

---

## Database Schema

**File:** `packages/db/prisma/schema.prisma`

```prisma
model User {
  id         String     @id @default(cuid())
  email      String     @unique
  apiKey     String     @unique
  credits    Int        @default(100)
  webhookUrl String?
  createdAt  DateTime   @default(now())
  jobs       Job[]
  creditLogs CreditLog[]
}

model CreditLog {
  id        String   @id @default(cuid())
  userId    String
  user      User     @relation(fields: [userId], references: [id])
  amount    Int
  reason    String
  jobId     String?
  createdAt DateTime @default(now())
}

model Job {
  id           String    @id @default(cuid())
  userId       String?
  status       String    @default("PENDING")  // PENDING | PROCESSING | DONE | FAILED
  inputUrl     String
  outputUrl    String?
  inputFormat  String
  outputFormat String
  error        String?
  createdAt    DateTime  @default(now())
  updatedAt    DateTime  @updatedAt
  user         User?     @relation(fields: [userId], references: [id])
}
```

---

## API Routes

### `GET /health`
- **Auth:** None
- **Response:** `{ "ok": true, "timestamp": "..." }`

---

### `POST /jobs`
- **Auth:** `Authorization: Bearer <apiKey>`
- **Body:** `multipart/form-data` with `file` (binary) and `outputFormat` (string)
- **Rate Limit:** 10 jobs/hour per user
- **Checks:** File present, outputFormat required, credits > 0 (402 if insufficient)
- **Process:**
  1. Extract extension as `inputFormat`
  2. Upload to R2 at `inputs/{jobId}/{filename}`
  3. Create Job in DB (status: PENDING)
  4. Push to BullMQ `conversions` queue
- **Response (201):** `{ "jobId": "...", "status": "PENDING", "message": "Job queued successfully" }`

---

### `GET /jobs/:id`
- **Auth:** `Authorization: Bearer <apiKey>`
- **Response:** Full job object + user credits
```json
{
  "id": "...", "status": "DONE", "inputUrl": "...", "outputUrl": "...",
  "inputFormat": "mp4", "outputFormat": "pdf", "error": null,
  "createdAt": "...", "updatedAt": "...", "credits": 99
}
```

---

### `PATCH /user/webhook`
- **Auth:** `Authorization: Bearer <apiKey>`
- **Body:** `{ "webhookUrl": "https://..." }`
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

### `POST /billing/orders`
- **Auth:** `Authorization: Bearer <apiKey>`
- **Requires:** `RAZORPAY_KEY_ID` configured (503 if missing)
- **Body:** `{ "pack": "starter" | "pro" | "enterprise" }`
- **Response:** `{ "orderId": "...", "amount": 19900, "currency": "INR", "credits": 500 }`

---

### `POST /billing/verify`
- **Auth:** `Authorization: Bearer <apiKey>`
- **Body:** `{ "orderId": "...", "paymentId": "...", "signature": "..." }`
- **Process:** Verify HMAC → fetch order → add credits → log CreditLog
- **Response:** `{ "ok": true, "credits": 600 }`

---

## Worker

**File:** `apps/worker/src/index.ts`

**Queue:** `conversions`

**Job data:**
```typescript
{
  jobId: string,
  inputUrl: string,      // Full R2 URL
  inputFormat: string,   // e.g. 'mp4'
  outputFormat: string,   // e.g. 'pdf'
  userId?: string
}
```

**Job options:**
```typescript
{
  attempts: 3,
  backoff: { type: "exponential", delay: 5000 },
  removeOnComplete: 100,
  removeOnFail: 200
}
```

**Processor steps:**
1. Update job status to `PROCESSING`
2. Download input from R2 to `/tmp/{jobId}-input.{inputFormat}`
3. Route:
   - Video/audio formats → FFmpeg
   - Document formats → LibreOffice headless
   - Unsupported → throw error
4. Upload output to R2 at `outputs/{jobId}/output.{outputFormat}`
5. Update job to `DONE`, set `outputUrl`
6. Deduct 1 credit, log to CreditLog
7. Send webhook (fire-and-forget)
8. Cleanup temp files

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

**Supported formats:**
- Video/Audio (FFmpeg): mp4, mov, avi, mkv, webm, mp3, wav, aac, flac
- Documents (LibreOffice): pdf, docx, doc, pptx, xlsx, odt, html, txt

---

## Queue

**File:** `packages/queue/src/index.ts`

- **Queue name:** `conversions`
- **Connection:** Redis via `REDIS_URL`
- **Retry:** 3 attempts with exponential backoff (5s delay)
- **Cleanup:** Remove completed jobs after 100, failed after 200

---

## Storage

**File:** `packages/storage/src/index.ts`

R2-backed S3-compatible storage:
- `uploadFile(key, filePath, mimeType)` → returns `{R2_PUBLIC_URL}/{key}`
- `downloadFile(key, destPath)` → streams to local file
- `deleteFile(key)` → deletes from R2
- `getSignedUrl(key, expiresInSeconds)` → presigned URL

**R2 key patterns:**
- Inputs: `inputs/{jobId}/{originalFilename}`
- Outputs: `outputs/{jobId}/output.{outputFormat}`

---

## Auth System

- Users have a unique `apiKey` stored in DB
- Every request must include `Authorization: Bearer <apiKey>` header
- API validates key against `User` table, attaches user to `req.user`
- No JWT/sessions — API key auth only
- Credits checked on job submission (402 if insufficient)

---

## Rate Limiting

**File:** `apps/api/src/middleware/rateLimiter.ts`

- **Global:** 100 requests/15min per IP (Redis-backed)
- **Job submit:** 10 jobs/hour per user (keyed by API key or IP)
- Both use `express-rate-limit` with `rate-limit-redis` store

---

## Cron Jobs

**File:** `apps/worker/src/cron/cleanup.ts`

- Runs hourly: `0 * * * *`
- Finds jobs older than 24h with status DONE or FAILED
- Deletes input and output files from R2
- Clears `outputUrl` and `inputUrl` in DB

---

## File Structure

```
zenvort/
├── apps/
│   ├── api/
│   │   ├── src/
│   │   │   ├── index.ts                 # Express app entry
│   │   │   ├── routes/
│   │   │   │   ├── jobs.ts             # POST /jobs, GET /jobs/:id
│   │   │   │   ├── user.ts             # PATCH /user/webhook
│   │   │   │   └── billing.ts          # GET/POST /billing/*
│   │   │   └── middleware/
│   │   │       └── rateLimiter.ts      # Global + job submit rate limits
│   │   ├── package.json
│   │   └── Dockerfile
│   └── worker/
│       ├── src/
│       │   ├── index.ts                # BullMQ worker, conversion logic
│       │   └── cron/
│       │       └── cleanup.ts          # Hourly file cleanup
│       ├── package.json
│       └── Dockerfile
├── packages/
│   ├── db/
│   │   ├── prisma/
│   │   │   ├── schema.prisma          # User, CreditLog, Job models
│   │   │   └── seed.ts                # Seeds test@zenvort.com
│   │   ├── src/index.ts               # PrismaClient singleton
│   │   └── package.json
│   ├── queue/
│   │   ├── src/
│   │   │   ├── index.ts               # conversions queue, job data type
│   │   │   └── connection.ts          # Redis connection
│   │   └── package.json
│   └── storage/
│       ├── src/index.ts               # R2 upload/download/delete
│       └── package.json
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
└── package.json
```

---

## Missing / TODO

| Feature | Status |
|---------|--------|
| Auth endpoints (signup/login) | Not implemented |
| List jobs endpoint | Not implemented |
| API key management | Not implemented |
| Admin routes | Not implemented |
| Usage/stats endpoint | Not implemented |
| Transactions endpoint | Not implemented |
| Dashboard frontend | `zenvort-dashboard/` exists (stub) |

---

## Roadmap

```
✅ Phase 1 — Working Core
✅ Phase 2 — Make it Usable  
✅ Phase 3 — Production Ready

🔜 Phase 4 — SaaS Web Dashboard
   [ ] Landing page with pricing
   [ ] User signup / login
   [ ] Dashboard with job upload + history
   [ ] API key management
   [ ] Credit balance display
   [ ] Admin panel

🔜 Phase 5 — Growth & Monetisation
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