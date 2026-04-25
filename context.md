# ZENVORT — Full Project Context

## What is Zenvort
A file conversion SaaS API. Users upload files → backend queues 
conversion job (FFmpeg/LibreOffice) → user polls or gets webhook 
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
│  CORS enabled (origin: *)                                    │
│  Rate limiting (Redis-backed)                                │
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
┌─────────────────────────────┐
│    apps/worker (BullMQ)     │
│  - FFmpeg (video/audio)     │
│  - LibreOffice (docs)        │
│  - Webhook sender             │
└─────────────────────────────┘
```

---

## Tech Stack
Node.js, TypeScript, Express, BullMQ, Redis, Prisma, PostgreSQL, 
Cloudflare R2, FFmpeg, LibreOffice, Docker, pnpm workspaces, **Vite + React + Tailwind CSS v4**

---

## Getting Started

```bash
# Start all services
docker-compose up --build -d

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

## Database Schema

**File:** `packages/db/prisma/schema.prisma`

```prisma
model User {
  id         String     @id @default(cuid())
  email      String     @unique
  password   String?     -- bcryptjs hashed, optional for legacy
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
}

model Job {
  id           String    @id @default(cuid())
  userId       String?
  status       String    @default("PENDING")  -- PENDING | PROCESSING | DONE | FAILED
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

### Auth

#### POST /auth/signup
- **Auth:** None
- **Body:** `{ email: string, password: string }`
- **Validation:** Email format, password min 8 chars, email unique
- **Process:** bcryptjs hash password, create user with 100 credits, log CreditLog (signup)
- **Response (201):** `{ apiKey: string, user: { id, email, credits, role } }`

#### POST /auth/login
- **Auth:** None
- **Body:** `{ email: string, password: string }`
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
- **Rate limit:** 10 jobs/hour per user
- **Checks:** File present, outputFormat required, credits > 0 (402 if insufficient)
- **Process:** Upload to R2 at `inputs/{jobId}/{filename}`, create Job (PENDING), push to BullMQ
- **Response (201):** `{ jobId: string, status: "PENDING", message: string }`

#### GET /jobs/:id
- **Auth:** `Authorization: Bearer <apiKey>`
- **Response:** Full job object

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
- **Response:** `{ users: [{ id, email, credits, role, createdAt, _count: { jobs } }], total, page, limit }`

#### PATCH /admin/users/:id/credits
- **Auth:** `Authorization: Bearer <apiKey>` + role=admin
- **Body:** `{ amount: number }` — positive to add, negative to deduct
- **Process:** Update user credits, log to CreditLog
- **Response:** `{ ok: true, credits: number }`

### Health

#### GET /health
- **Auth:** None
- **Response:** `{ ok: true, timestamp: "..." }`

---

## Worker

**File:** `apps/worker/src/index.ts`

**Queue:** `conversions` (BullMQ)

**Job data:**
```typescript
{
  jobId: string,
  inputUrl: string,      // Full R2 URL
  inputFormat: string,  // e.g. 'mp4'
  outputFormat: string,  // e.g. 'pdf'
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
1. Update job status to PROCESSING
2. Download input from R2 to `/tmp/{jobId}-input.{inputFormat}`
3. Route: video/audio → FFmpeg, documents → LibreOffice headless
4. Upload output to R2 at `outputs/{jobId}/output.{outputFormat}`
5. Update job to DONE, set outputUrl
6. Deduct 1 credit, log to CreditLog
7. Send webhook to user.webhookUrl (fire and forget)
8. Cleanup temp files

**Webhook payload:**
```json
{ "jobId": "...", "status": "DONE" | "FAILED", "outputUrl": "...", "error": "...", "timestamp": "..." }
```

**Supported formats:**
- FFmpeg: mp4, mov, avi, mkv, webm, mp3, wav, aac, flac
- LibreOffice: pdf, docx, doc, pptx, xlsx, odt, html, txt

---

## Queue

**File:** `packages/queue/src/index.ts`
- Queue name: `conversions`
- Connection: Redis via REDIS_URL
- Retry: 3 attempts, exponential backoff (5s delay)

---

## Storage

**File:** `packages/storage/src/index.ts`
- R2/S3-compatible storage
- uploadFile(key, path) → `{R2_PUBLIC_URL}/{key}`
- downloadFile(key, destPath)
- deleteFile(key)
- getSignedUrl(key, seconds)

**R2 key patterns:**
- Inputs: `inputs/{jobId}/{originalFilename}`
- Outputs: `outputs/{jobId}/output.{outputFormat}`

---

## Auth System
- Users have unique apiKey stored in DB
- All requests: `Authorization: Bearer <apiKey>`
- Passwords: bcryptjs hashed
- Roles: "user" (default) or "admin"
- No JWT — API key auth only

---

## Rate Limiting

**File:** `apps/api/src/middleware/rateLimiter.ts`
- Global: 100 requests/15min per IP (Redis-backed)
- Job submit: 10 jobs/hour per user (keyed by API key or IP)

---

## Cron Jobs

**File:** `apps/worker/src/cron/cleanup.ts`
- Runs hourly: `0 * * * *`
- Deletes R2 files for jobs older than 24h with status DONE/FAILED
- Clears outputUrl and inputUrl in DB

---

## Frontend (zenvort-dashboard/)

**Stack:** Vite + React 18 + React Router v6 + Tailwind CSS v4 + Axios

**Dev server:** `npm run dev` → http://localhost:5173

**Build:** `npm run build` → dist/

**Routes (react-router-dom v6):**
- `/` — Landing page (public)
- `/login` — Email/password login
- `/signup` — Email/password signup
- `/dashboard` — Stats + upload form + job list (protected)
- `/keys` — API key reveal/copy + webhook config (protected)
- `/billing` — Credit balance + transactions (protected)
- `/admin` — Platform stats + user table (protected, admin only)

**Auth storage (localStorage):**
- `zenvort_api_key` — API key string
- `zenvort_user` — JSON user object

**File structure:**
```
zenvort-dashboard/
├── src/
│   ├── main.jsx              -- Entry point
│   ├── App.jsx               -- Router + layout
│   ├── api.js                -- API calls (axios/fetch)
│   ├── store.js              -- localStorage helpers
│   ├── index.css             -- Tailwind directives + custom styles
│   ├── pages/
│   │   ├── Landing.jsx       -- Marketing page (hero, features, pricing, footer)
│   │   ├── Login.jsx         -- Sign in form
│   │   ├── Signup.jsx        -- Create account form
│   │   ├── Dashboard.jsx     -- Stats + file upload + job table
│   │   ├── ApiKey.jsx        -- API key display + webhook config
│   │   ├── Billing.jsx        -- Credit balance + transactions
│   │   └── Admin.jsx         -- User management + platform stats
│   └── components/
│       ├── Sidebar.jsx       -- Dark sidebar navigation
│       ├── Navbar.jsx        -- Top bar with mobile menu
│       ├── StatCard.jsx      -- Metric display card
│       ├── JobTable.jsx      -- Paginated job list
│       ├── Toast.jsx         -- Toast notifications
│       └── Spinner.jsx       -- Loading spinner
├── index.html
├── tailwind.config.js
├── postcss.config.js
└── package.json
```

**Design system:**
- Font: DM Sans (Google Fonts)
- Accent: indigo-600 (#6366f1)
- Sidebar: bg-slate-900
- Content: bg-slate-50
- Cards: bg-white rounded-xl border border-slate-200
- Status badges: rounded-full px-2 py-1 text-xs font-medium
  - PENDING: bg-amber-100 text-amber-800
  - PROCESSING: bg-blue-100 text-blue-800
  - DONE: bg-emerald-100 text-emerald-800
  - FAILED: bg-red-100 text-red-800

---

## Testing

```powershell
# Health check
curl http://localhost:3000/health

# Sign up via API
Invoke-RestMethod -Uri "http://localhost:3000/auth/signup" -Method POST -ContentType "application/json" -Body '{"email":"test@example.com","password":"password123"}'

# Login
Invoke-RestMethod -Uri "http://localhost:3000/auth/login" -Method POST -ContentType "application/json" -Body '{"email":"test@example.com","password":"password123"}'

# Open frontend
# http://localhost:5173
```

---

## Test Credentials

Seeded user (no password — use Sign Up to create account):
- Email: test@zenvort.com
- API Key: test-key-123
- Role: admin

For login, either:
1. Sign up via UI to create account with password
2. Or set password manually in postgres:
```sql
UPDATE "User" SET "password" = '$2a$10$YOUR_HASH' WHERE "email" = 'test@zenvort.com';
```

---

## Known Issues (RESOLVED)

- **OLD: Single-file HTML with Preact + HTM had JavaScript syntax errors** → Fixed by migrating to Vite + React
- **OLD: file:// origin iframe/postMessage errors** → Fixed (no longer using file:// URLs)
- **OLD: Tailwind not compiling** → Fixed by using @tailwindcss/postcss v4 + `@import "tailwindcss"` syntax

---

## Roadmap

```
✅ Phase 1 — Working Core
✅ Phase 2 — Make it Usable
✅ Phase 3 — Production Ready
✅ Phase 4 — SaaS Web Dashboard (Vite + React + Tailwind)
✅ FIXED — Frontend syntax errors and styling

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