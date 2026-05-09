# Zenvort — Test Checklist

**Environment:** docker-compose stack (api, worker, redis, gotenberg)
**Prerequisites:** `INTERNAL_SECRET`, `R2_*`, `ADMIN_API_KEY` set in `.env`

---

## Auth

### Signup

- [ ] `POST /auth/signup` — valid email + 8+ char password → 201 + `apiKey`
- [ ] `POST /auth/signup` — duplicate email → 409
- [ ] `POST /auth/signup` — short password → 422

### Login

- [ ] `POST /auth/login` — correct credentials → 200 + `apiKey`
- [ ] `POST /auth/login` — wrong password → 401
- [ ] `POST /auth/login` — unknown email → 401

---

## Formats

- [ ] `GET /formats` → 200, list of 29 formats
- [ ] `GET /formats/pdf` → 200, outputs: docx, txt, html, png, jpg
- [ ] `GET /formats/unknown` → 404

---

## Jobs

### Create Job (authenticated)

- [ ] `POST /jobs` — valid file + outputFormat → 201 + `jobId` + "PENDING"
- [ ] `POST /jobs` — missing file → 422
- [ ] `POST /jobs` — unsupported input format → 400
- [ ] `POST /jobs` — unsupported output format → 400
- [ ] `POST /jobs` — same input/output format → 400
- [ ] `POST /jobs` — daily limit reached (≥50 today) → 429

### List Jobs

- [ ] `GET /jobs` — authenticated → 200, paginated list
- [ ] `GET /jobs` — bad Bearer token → 401

### Get Job

- [ ] `GET /jobs/{id}` — own job → 200 with signed `outputUrl`
- [ ] `GET /jobs/{id}` — not own job → 403
- [ ] `GET /jobs/{id}` — unknown job → 404
- [ ] `GET /jobs/{id}` — anonymous, job has `user_id` → 401

---

## User

- [ ] `GET /user/me` → 200, includes `dailyUsage`, `dailyLimit`, `quotaResetAt`
- [ ] `PATCH /user/webhook` — valid public URL → 200
- [ ] `PATCH /user/webhook` — private IP (e.g. `http://localhost/...`) → 400

---

## Rate Limiting

- [ ] Exceed 100 job submits/hour → 429
- [ ] Exceed 100 job reads/minute → 429
- [ ] Exceed 30 login attempts/15 min → 429
- [ ] Exceed 5000 signups/hour → 429

---

## Worker

- [ ] Job status transitions: pending → processing → done (or failed)
- [ ] `GET /jobs/{id}` after done → `outputUrl` + `expiresAt`
- [ ] `GET /jobs/{id}` after 20 min → `outputUrl` is null (file deleted)
- [ ] Conversion error → `error` field sanitized (no library names)
- [ ] Webhook fires (if `webhookUrl` set) on job completion

---

## Admin

- [ ] `GET /admin/users` — admin user → 200, paginated user list
- [ ] `GET /admin/users` — regular user → 403
- [ ] `GET /admin/stats` → 200, `{ totalUsers, totalJobs, jobsByStatus }`

---

## CLI smoke test

```bash
# Signup
KEY=$(curl -s -X POST http://localhost:3000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['apiKey'])")

# Create job
curl -X POST http://localhost:3000/jobs \
  -H "Authorization: Bearer $KEY" \
  -F "file=@/etc/passwd" \
  -F "outputFormat=txt"

# Poll
sleep 5 && curl http://localhost:3000/jobs \
  -H "Authorization: Bearer $KEY"

# Check user profile (daily usage)
curl http://localhost:3000/user/me \
  -H "Authorization: Bearer $KEY"
```

---

## Logs

```bash
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f redis
docker compose logs -f gotenberg
```