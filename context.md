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
│                    apps/api (Express, :3000)                  │
│  /auth/*, /jobs, /user, /billing, /admin                    │
│  Helmet security headers (enabled)                          │
│  CORS: allowlist only (no wildcard)                         │
│  Rate limiting: global + login + signup + job submit       │
└─────────────────────────────┬────────────────────────────────┘
                              │ Prisma
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
│              apps/worker (BullMQ v5)                         │
│  - Converter routing table with fallback chains              │
│  - Job caching (re-use DONE outputs for identical inputs)     │
│  - Metrics server (:3001, internal only)                     │
│  - Orphan file cleanup (10min interval, 30min max age)       │
│  - Semaphore: max WORKER_CONCURRENCY concurrent conversions  │
│  - Disk space guard: 2GB /tmp/zenvort/ limit                │
│  - Webhook sender                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech Stack
Node.js, TypeScript, Express, BullMQ (v5), Redis, Prisma, PostgreSQL,
Cloudflare R2 (@aws-sdk/client-s3), FFmpeg, LibreOffice, pdftoppm, pdftotext,
Pandoc, Sharp, ImageMagick, Ghostscript, Docker, pnpm workspaces,
**Vite + React 19 + Tailwind CSS v3 + shadcn/ui + React Router v7**

---

## Getting Started

```bash
# Start all services
docker-compose up --build -d

# Run migrations (first time or after schema changes)
pnpm exec prisma migrate dev --name <migration_name>

# Check API health
curl http://localhost:3000/health

# Worker metrics (internal only)
curl http://localhost:3001/metrics

# Open frontend (Vite dev server)
cd zenvort-dashboard
npm run dev  # http://localhost:5173
```

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
| `ALLOWED_ORIGIN` | No | `http://localhost:5173` | CORS allowlist (frontend URL) |
| `RAZORPAY_KEY_ID` | For billing | — | Razorpay API key |
| `RAZORPAY_KEY_SECRET` | For billing | — | Razorpay secret |
| `WORKER_CONCURRENCY` | No | `3` | BullMQ + semaphore concurrency limit |

---

## Packages

| Package | Path | Purpose |
|---------|------|---------|
| `@zenvort/db` | `packages/db/` | Prisma client + schema |
| `@zenvort/queue` | `packages/queue/` | BullMQ queue + Redis connection |
| `@zenvort/storage` | `packages/storage/` | R2/S3 upload/download/delete |
| `@zenvort/shared` | `packages/shared/` | ROUTE_KEYS, getSupportedFormats, ConverterFn types |
| `@zenvort/api` | `apps/api/` | Express API server |
| `@zenvort/worker` | `apps/worker/` | BullMQ job processor |

---

## Database Schema

**File:** `packages/db/prisma/schema.prisma`

```prisma
model User {
  id         String     @id @default(cuid())
  email      String     @unique
  password   String?
  apiKey     String     @unique
  credits    Int        @default(100)
  role       String     @default("user")  -- "user" or "admin"
  webhookUrl String?
  createdAt  DateTime   @default(now())
  jobs       Job[]
  creditLogs CreditLog[]
}

model CreditLog {
  id        String   @id @default(cuid())
  userId    String
  user      User    @relation(fields: [userId], references: [id])
  amount    Int
  reason    String   -- 'signup' | 'conversion' | 'purchase' | 'manual_add' | 'manual_deduct'
  jobId     String?
  createdAt DateTime @default(now())

  @@index([userId])
  @@index([userId, createdAt(sort: Desc)])
}

model Job {
  id            String    @id @default(cuid())
  userId        String?
  status        String    @default("PENDING")  -- PENDING | PROCESSING | DONE | FAILED
  inputUrl      String
  outputUrl     String?
  inputFormat   String
  outputFormat  String
  error         String?
  converterUsed String?   -- which converter succeeded (e.g. "pdftotext", "sharp")
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt
  user          User?     @relation(fields: [userId], references: [id])

  @@index([userId])
  @@index([status])
  @@index([userId, createdAt(sort: Desc)])
  @@index([inputUrl, outputFormat, status])  -- job caching lookup
}
```

---

## Worker File Structure

```
apps/worker/src/
├── index.ts                    -- BullMQ processor, startup bootstrap
├── routes.ts                   -- ROUTES Map: key → { converters, description }
├── executor.ts                -- Fallback chain: executeConversion()
│
├── converters/
│   ├── libreoffice.ts         -- soffice --headless + loMutex + --user-installation
│   ├── ffmpeg.ts              -- fluent-ffmpeg
│   ├── pdftoppm.ts            -- spawn() pdftoppm (PDF → PNG/JPG)
│   ├── pdftotext.ts           -- spawn() pdftotext
│   ├── pandoc.ts              -- spawn() pandoc
│   ├── sharp.ts                -- Sharp pipeline
│   ├── imagemagick.ts          -- spawn() convert
│   └── ghostscript.ts         -- spawn() gs -dSAFER
│
├── security/
│   ├── pathGuard.ts           -- sanitizeAndAssertTmpPath(), TMP_DIR = /tmp/zenvort
│   ├── semaphore.ts           -- acquireSemaphore(), checkDiskSpace() (2GB limit)
│   ├── mimeGuard.ts           -- assertMimeTypeMatches() via file-type
│   └── loMutex.ts             -- async-mutex Mutex for LibreOffice serialization
│
├── metrics.ts                 -- In-memory metrics (conversionCount, avgDurationMs,
│                                -- fallbackRate, cacheHitCount) — GET :3001/metrics
├── cleanup.ts                 -- Metrics server (Express :3001) + orphan cleanup
│                                -- (10min interval, 30min max age via setInterval)
├── cron/cleanup.ts            -- Hourly R2 cleanup of old DONE/FAILED jobs (24h)
└── scripts/clearStaleJobs.ts   -- Drains stale BullMQ jobs + marks stale PENDING rows FAILED
```

---

## Converter Routing Table

**Source of truth:** `packages/shared/src/routes.ts` (ROUTE_KEYS) + `apps/worker/src/routes.ts` (full Map with converter functions).

`getSupportedFormats()` in `@zenvort/shared` derives `inputFormats`, `outputFormats`, and all supported pairs dynamically from `ROUTE_KEYS`. The API (`apps/api/src/routes/jobs.ts`) imports it — adding a key to `ROUTE_KEYS` automatically enables validation with no other changes.

All routes:
- Image→Image: jpg/png/webp/avif, png/webp/avif/jpg/pdf, gif, tiff, bmp (sharp → imagemagick)
- PDF: png, jpg, txt (pdftotext → libreoffice), docx, html, pdf compression (ghostscript)
- Documents: docx/doc/odt ↔ pdf/html/txt/docx (libreoffice → pandoc)
- Markdown: md → pdf/docx/html/txt (pandoc → libreoffice)
- HTML: html → pdf/docx/txt/md (libreoffice → pandoc)
- Spreadsheets: xlsx/csv/ods ↔ csv/ods/xlsx/pdf (libreoffice)
- Presentations: pptx ↔ pdf/odp, odp ↔ pdf/pptx (libreoffice)
- Audio: mp3/wav/aac/flac/ogg/m4a/opus/wma ↔ (ffmpeg)
- Video: mp4/webm/mov/avi/mkv/flv/wmv/mts/ts ↔ (ffmpeg)

**Fallback chain logic** (`apps/worker/src/executor.ts`):
1. Validate jobId is UUID
2. Assert all paths under `/tmp/zenvort/`
3. Look up route via `getRoute(inputFormat, outputFormat)` — throw if no route
4. For each converter in order:
   - Delete outputPath (clean slate)
   - Run converter, measure duration via `performance.now()`
   - On success: return `{ converterUsed, attempts }`
   - On failure: record attempt, log "timed out" vs "failed", continue to next
5. If all fail: throw aggregated error listing each converter + error

---

## Worker Startup Sequence (index.ts)

```
1. mkdir /tmp/zenvort (recursive, async — logs error if fails)
2. sharp.concurrency(1) — limit libvips to 1 thread
3. startMetricsServer() — Express :3001, routes /metrics + /health
4. startOrphanCleanup() — setInterval every 10 min
5. BullMQ Worker instantiated last
```

---

## processJob Flow (apps/worker/src/index.ts)

```
a. Guard: inputFormat === outputFormat → FAILED + { unrecoverable: true } + webhook
b. Log: [worker][jobId] Job received { inputFormat, outputFormat, userId }
c. acquireSemaphore() → { retryable: true } if at capacity
d. checkDiskSpace() → { retryable: true } if /tmp/zenvort/ > 2GB
e. Cache lookup: db.job.findFirst({ inputUrl, outputFormat, status: DONE })
   → if hit: mark DONE, webhook, recordCacheHit(), return (no credit deducted)
f. db.job.update status = PROCESSING
g. Download from R2:
   - inputKey = inputUrl.replace(R2_PUBLIC_URL + "/", "")
   - urlPathSegment = inputUrl.split("/").pop() ?? ""   ← extracts filename from URL path
   - rawExt = path.extname(urlPathSegment).replace(/^\./, "")   ← strips leading dot
   - actualExt = rawExt || inputFormat   ← fallback to inputFormat if URL has no extension
   - inputPath = /tmp/zenvort/{jobId}-input.{actualExt}
h. stat(inputPath) → >200MB → { unrecoverable: true } + delete file
i. Log: [worker][jobId] Conversion started { routeFound, converterCount }
j. executeConversion() — fallback chain via getRoute() from routes.ts
k. Log: [worker][jobId] Conversion done { converterUsed, totalDurationMs, attempts }
l. stat(outputPath) → >500MB → delete outputPath + { unrecoverable: true }
m. assertMimeTypeMatches(outputPath, outputFormat, jobId) via file-type
n. uploadFile() to R2 outputs/{jobId}/output.{outputFormat}
o. Delete inputPath + outputPath immediately (before DB update)
p. db.job.update status = DONE, outputUrl = r2Url, converterUsed = <name>
q. recordSuccess() + recordFallbackUsage() metrics
r. Credit deduction: db.user.update credits - 1 + CreditLog entry
s. Webhook fire-and-forget
t. finally: releaseSemaphore() + deleteIfExists(inputPath) + deleteIfExists(outputPath)
```

**Error handling (3-tier):**
- `{ retryable: true }` → do NOT mark FAILED, re-throw → BullMQ retries
- `{ unrecoverable: true }` → mark FAILED, throw with unrecoverable flag → BullMQ does NOT retry
- everything else → mark FAILED on last attempt, re-throw → BullMQ retries up to maxAttempts

---

## API Routes

### Auth

#### POST /auth/signup
- **Auth:** None
- **Body:** `{ email: string, password: string }`
- **Validation:** Email format, password min 8 chars, email unique
- **Rate limit:** 5 attempts/hour per IP (signupLimiter, skipSuccessfulRequests: true)
- **Process:** bcryptjs hash password, create user with 100 credits, log CreditLog (signup)
- **Response (201):** `{ apiKey: string, user: { id, email, credits, role } }`

#### POST /auth/login
- **Auth:** None
- **Body:** `{ email: string, password: string }`
- **Rate limit:** 5 attempts/15min per IP (loginLimiter, skipSuccessfulRequests: true)
- **Process:** Find user, bcryptjs compare password
- **Response:** `{ apiKey: string, user: { id, email, credits, role, webhookUrl } }`
- **Error:** 401 if user not found or password wrong

### User

#### GET /user/me
- **Auth:** `Authorization: Bearer <apiKey>`
- **Response:** `{ id, email, credits, webhookUrl, role, createdAt }`

#### PATCH /user/webhook
- **Auth:** `Authorization: Bearer <apiKey>`
- **Body:** `{ webhookUrl: string }`
- **Validation:** Valid URL format
- **Response:** `{ ok: true, webhookUrl: string }`

### Jobs

#### GET /jobs
- **Auth:** `Authorization: Bearer <apiKey>`
- **Query:** `?page=1&limit=20`
- **Response:** `{ jobs: [...], total: number, page: number, limit: number }`

#### POST /jobs
- **Auth:** `Authorization: Bearer <apiKey>`
- **Body:** multipart/form-data — `file` (binary) + `outputFormat` (string)
- **Rate limit:** 10 jobs/hour per user (keyed on userId from DB, not IP)
- **File size limit:** 100MB max (413 if exceeded)
- **Checks:** File present, outputFormat required, credits > 0 (402 if insufficient)
- **Input format:** Inferred from file extension
- **Format validation:** `getSupportedFormats()` from `@zenvort/shared` — adding a key to ROUTE_KEYS enables validation automatically
- **Process:** Upload to R2 at `inputs/{jobId}/{safeName}`, create Job (PENDING), push to BullMQ
- **Path sanitization:** `file.originalname` sanitized to alphanumeric + `_.-`
- **Response (201):** `{ jobId: string, status: "PENDING", message: string }`

#### GET /jobs/:id
- **Auth:** `Authorization: Bearer <apiKey>`
- **Authorization:** Returns 403 if job does not belong to authenticated user
- **Response:** Full job object including `converterUsed` field

### Billing

#### GET /billing/plans
- **Auth:** None
- **Response:**
```json
[
  { "pack": "starter", "credits": 500, "amount": 199, "currency": "INR", "name": "Starter Pack" },
  { "pack": "pro", "credits": 2000, "amount": 599, "currency": "INR", "name": "Pro Pack" },
  { "pack": "enterprise", "credits": 10000, "amount": 1999, "currency": "INR", "name": "Enterprise Pack" }
]
```

#### GET /billing/usage
- **Auth:** `Authorization: Bearer <apiKey>`
- **Response:**
```json
{
  "credits": 100,
  "totalJobs": 45,
  "jobsToday": 3,
  "successRate": 95,
  "dailyUsage": [{ "date": "2024-04-01", "count": 5 }, ...]  -- last 30 days
}
```

#### GET /billing/transactions
- **Auth:** `Authorization: Bearer <apiKey>`
- **Response:** `{ logs: [{ id, amount, reason, jobId, createdAt }] }`

#### POST /billing/orders
- **Auth:** `Authorization: Bearer <apiKey>`
- **Body:** `{ pack: "starter" | "pro" | "enterprise" }`
- **Requires:** RAZORPAY_KEY_ID env var
- **Response:** `{ orderId, amount, currency, credits }`

#### POST /billing/verify
- **Auth:** `Authorization: Bearer <apiKey>`
- **Body:** `{ orderId, paymentId, signature }`
- **Process:** Verify HMAC → fetch Razorpay order → add credits → log

### Admin

#### GET /admin/stats
- **Auth:** `Authorization: Bearer <apiKey>` + role=admin
- **Response:** `{ totalUsers, totalJobs, jobsToday, activeJobs }`

#### GET /admin/users
- **Auth:** `Authorization: Bearer <apiKey>` + role=admin
- **Query:** `?page=1`
- **Response:** `{ users: [...], total, page, limit }`

#### PATCH /admin/users/:id/credits
- **Auth:** `Authorization: Bearer <apiKey>` + role=admin
- **Body:** `{ amount: number }`
- **Process:** Update user credits, log to CreditLog
- **Response:** `{ ok: true, credits: number }`

### Health

#### GET /health
- **Auth:** None
- **Response:** `{ ok: true, timestamp: "..." }`

---

## Queue

**File:** `packages/queue/src/index.ts`
- Queue name: `conversions`
- Connection: Redis via `redisConnection` (named export from `packages/queue/src/connection.ts`)
- Retry: 3 attempts, exponential backoff (5s delay)
- BullMQ v5 does not support `timeout` in job options — enforced via Worker lockDuration

### Drain script

**File:** `apps/worker/src/scripts/clearStaleJobs.ts`

Drains stale jobs from the queue and marks stale DB rows as FAILED. Used to clean up jobs that were queued before `inputFormat` validation was added.

```bash
# Requires CUTOFF_DATE env var (ISO 8601)
CUTOFF_DATE=2026-03-01T00:00:00Z node --import tsx apps/worker/src/scripts/clearStaleJobs.ts
```

- Connects to BullMQ `conversions` queue, calls `.clean()` on waiting/delayed/failed states
- Queries Prisma: `Job` rows where `status = 'PENDING'` and `createdAt < CUTOFF_DATE` → `status = 'FAILED'` with `error = 'Cleared: malformed inputFormat from pre-validation queue'`
- Logs counts of affected BullMQ jobs and DB rows
- Requires `CUTOFF_DATE` env var; exits with code 1 if missing or invalid

---

## Storage

**File:** `packages/storage/src/index.ts`
- R2/S3-compatible storage via @aws-sdk/client-s3
- uploadFile(key, path, mimeType)
- downloadFile(key, destPath) — validates body non-null
- deleteFile(key)
- getSignedUrl(key, seconds)

**R2 key patterns:**
- Inputs: `inputs/{jobId}/{safeName}`
- Outputs: `outputs/{jobId}/output.{outputFormat}`

---

## Auth System
- Users have unique apiKey in DB
- All requests: `Authorization: Bearer <apiKey>`
- Passwords: bcryptjs hashed (cost factor: 10)
- Roles: "user" (default) or "admin"
- No JWT — API key auth only

---

## Security

**Helmet:** `apps/api/src/index.ts` — helmet v7 middleware enabled

**CORS:** `apps/api/src/index.ts`
- No wildcard `origin: '*'`
- Allowlist: `ALLOWED_ORIGIN` env var
- Callback form: `cors({ origin: allowedList.includes(origin) ? origin : false, credentials: true })`

**Format validation:** `apps/api/src/routes/jobs.ts`
- Imported from `@zenvort/shared` via `getSupportedFormats()` — live from routing table

**Path traversal protection:**
- API: `file.originalname` sanitized with regex, `path.basename()` used as R2 key
- Worker: All paths go through `sanitizeAndAssertTmpPath()` — must resolve under `/tmp/zenvort/`

**Worker file bounds:** `/tmp/zenvort/` — dedicated subdirectory, not bare `/tmp/`

**Job submit rate limiter:** Keyed on `user.id` from DB lookup of API key, not raw IP

**File size limits:**
- API upload: 100MB (multer)
- Worker input: 200MB (checked after download via `stat`)
- Worker output: 500MB (checked after conversion via `stat`)

**IDOR protection:** GET /jobs/:id checks `job.userId === req.user.id`

**Brute force protection:** loginLimiter + signupLimiter with skipSuccessfulRequests

**Shell injection prevention:**
- All converters use `spawn()` with argument arrays — no `exec()`, no template strings
- All file paths validated by `sanitizeAndAssertTmpPath()` before any system call

**LibreOffice concurrency:** `libreofficeMutex.runExclusive()` serializes all LO conversions in-process; each job gets `--user-installation=/tmp/zenvort/lo-profile-<jobId>`

---

## Metrics (apps/worker/src/metrics.ts)

In-memory, reset on worker restart. Exposed via `GET :3001/metrics` (internal only).

```typescript
interface MetricsSnapshot {
  conversionCount: Record<string, number>;              // "converter:format" → count
  conversionFailureCount: Record<string, number>;       // "converter:errorType" → count
  averageDurationMs: Record<string, number>;           // converter → running mean (Welford)
  fallbackRateByRoute: Record<string, { rate, total, fallbackCount }>;
  cacheHitCount: number;
  totalConversions: number;
  totalFailures: number;
}
```

Error types for failure tracking: `"timeout" | "failed" | "unsupported"`

---

## Cron Jobs

**apps/worker/src/cleanup.ts** — Internal services started at worker boot:
- Metrics HTTP server: Express on `:3001` (`/metrics` + `/health`), not publicly exposed
- Orphan cleanup: `setInterval` every 10 minutes, deletes files in `/tmp/zenvort/` older than 30 minutes

**apps/worker/src/cron/cleanup.ts** — R2 cleanup:
- Runs hourly: `0 * * * *`
- Deletes R2 files for jobs older than 24h with status DONE/FAILED
- Clears outputUrl and inputUrl in DB

---

## Frontend (zenvort-dashboard/)

**Stack:** Vite + React 19 + React Router v7 + Tailwind CSS v3 + shadcn/ui + Lucide React

**Dev server:** `npm run dev` → http://localhost:5173

**Routes:**
- `/` — Landing page (public)
- `/login` — Email/password login (real API)
- `/signup` — Email/password signup (real API)
- `/dashboard` — Stats + upload form + job list (real API)
- `/api-key` — API key display + copy (protected)
- `/billing` — Credit balance + plan selection (real API)
- `/admin` — User table + platform stats (real API, admin only)

**Auth storage:** `zenvort_api_key` (localStorage), `zenvort_user` (localStorage)

---

## Testing

```bash
# Health check
curl http://localhost:3000/health

# Worker metrics (internal)
curl http://localhost:3001/metrics

# Sign up via API
curl http://localhost:3000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Login
curl http://localhost:3000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Open frontend
# http://localhost:5173
```

---

## Test Credentials

Seeded user (no password — use Sign Up to create account):
- Email: test@zenvort.com
- API Key: test-key-123
- Role: admin

---

## Known Issues (RESOLVED)

- **OLD: path.extname() called on full inputUrl** → Fixed: `inputUrl.split("/").pop()` isolates filename segment, then `path.extname()` extracts extension — avoids `.r2.dev` being picked up as extension
- **OLD: Pre-rebuild jobs with malformed inputFormat** → Fixed: inputFormat === outputFormat guard + `clearStaleJobs.ts` drain script
- **OLD: FFmpeg routed for PDF→PNG/JPG (no PDF support)** → Fixed: `getRoute()` correctly routes PDF→image to `pdftoppm` (Sharp fallback), not FFmpeg
- **OLD: No path traversal protection in worker** → Fixed: `sanitizeAndAssertTmpPath()` + `/tmp/zenvort/` subdirectory
- **OLD: Shell injection in converter commands** → Fixed: all converters use `spawn()` with argument arrays
- **OLD: LibreOffice profile conflicts at concurrency > 1** → Fixed: `libreofficeMutex.runExclusive()` + `--user-installation`
- **OLD: Worker at max concurrency without conversion-level enforcement** → Fixed: `acquireSemaphore()` + `releaseSemaphore()`
- **OLD: No disk space guard on /tmp/** → Fixed: `checkDiskSpace()` throws retryable error if > 2GB
- **OLD: Converter outputting wrong MIME type silently** → Fixed: `assertMimeTypeMatches()` via file-type before R2 upload
- **OLD: Job submit rate limiter keyed on raw API key (no DB verification)** → Fixed: `keyGenerator` looks up userId from DB
- **OLD: Retryable errors marking jobs FAILED** → Fixed: retryable errors skip FAILED DB update, BullMQ retries
- **OLD: No conversion metrics** → Fixed: in-memory metrics in `metrics.ts` + GET :3001/metrics
- **OLD: No orphan cleanup of stale temp files** → Fixed: 10min setInterval cleanup of files > 30min old in cleanup.ts
- **OLD: Sharp spawning excessive libvips threads** → Fixed: `sharp.concurrency(1)` at startup
- **OLD: No job result caching** → Fixed: cache lookup by (inputUrl, outputFormat, status=DONE) before conversion
- **OLD: Format validation not driven by routing table** → Fixed: `getSupportedFormats()` from `ROUTE_KEYS` in `@zenvort/shared`
- **OLD: redisConnection imported as default export in queue index** → Fixed: changed to named import `import { redisConnection } from "./connection.js"`
- **OLD: @zenvort/shared not in Dockerfile workspace copy** → Fixed: both API and worker Dockerfiles include `COPY packages/shared/package.json packages/shared/`
- **OLD: Worker missing @types/express devDependency** → Fixed: added `@types/express` to worker package.json

---

## Remaining Work

- [ ] Upgrade bcrypt cost factor from 10 to 12
- [ ] Hash API keys in DB with SHA-256
- [ ] Email verification on signup
- [ ] Password reset flow
- [ ] ToS acceptance on signup
- [ ] Live Razorpay integration
- [ ] Credit purchase flow
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
✅ Phase 1 — Working Core
✅ Phase 2 — Make it Usable
✅ Phase 3 — Production Ready
✅ Phase 4 — SaaS Web Dashboard (Vite + React + shadcn/ui + Tailwind v3)
✅ Phase 5 — Growth & Monetisation (partial: billing routes exist, Razorpay not live)
✅ FIXED — Frontend wiring to real API
✅ FIXED — All critical security issues (IDOR, CORS, rate limiting, format validation, path traversal, file size, shell injection)
✅ FIXED — Worker reliability (timeouts, lockDuration, DB indexes)
✅ FIXED — Converter routing table with fallback chains
✅ FIXED — Worker metrics + orphan cleanup
✅ FIXED — Job result caching
✅ FIXED — MIME type validation before R2 upload
✅ FIXED — Disk space guard + concurrency semaphore
✅ FIXED — LibreOffice mutex + per-job profile

🔜 Phase 5 (continued)
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
