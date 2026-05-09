# Zenvort Backend Refactor — Execution Plan

## Prompt 1 — Delete dead code and stale artifacts [DONE]
- Delete: `bot/` directory, `nginx/telegram.conf`
- Clean README.md (remove Telegram bot refs, update storage/retention, add formats endpoint)
- Clean SETUP.md (remove Telegram bot setup, update service table)
- Update .env.example (remove BOT_TOKEN, ADMIN_TELEGRAM_IDS, WEBHOOK_BASE_URL, API_BASE_URL)
- Run `python -m compileall -q api worker`

## Prompt 2 — Fix all bugs identified in the audit [DONE]
- BUG 1: Anonymous users can read private job status (api/routes/jobs.py)
- BUG 2: Gotenberg URL mismatch (skip if done in P1)
- BUG 3: Unnecessary X-Internal-Secret on public routes (was bot/zenvort_client.py — bot removed)

## Prompt 3 — Restructure and clean the API layer [DONE]
- api/database.py: Add `get_db` async context manager
- api/routes/jobs.py: Extract `_get_signed_url()` and `_expires_at()` helpers
- api/routes/auth.py: Extract `_hash_password()` and `_generate_api_key()` helpers
- api/schemas.py: Add daily usage fields, docstrings
- api/main.py: Add CORS middleware, startup config log
- Added api/routes/formats.py: GET /formats, GET /formats/{fmt}
- Run `python -m compileall -q api`

## Prompt 4 — Restructure and clean the Worker layer [PENDING]
- worker/tasks.py: Extract `_r2_download()`, `_r2_upload()`, `_r2_delete()` helpers
- worker/executor.py: Add docstring to dispatch, add logging to bare excepts
- worker/routes.py: Add section comments, group routes
- worker/security/: Use specific exception types
- Run `python -m compileall -q worker`

## Prompt 5 — Bot layer [N/A — removed]
- Bot infrastructure removed entirely (Phase 2 migration complete)
- Daily quota enforcement moved to POST /jobs in api/routes/jobs.py
- Daily usage tracking added to GET /user/me in api/routes/user.py
- Webhook callback already implemented in worker/tasks.py (_fire_webhook)

## Prompt 6 — Final consistency pass + Docker config fix [PENDING]
- docker-compose.yml: Verify service definitions, add restart/logging config
- SETUP.md: Verify/correct stack docs, remove stale refs (done)
- README.md: Full rewrite complete
- Search for hardcoded localhost/ports, replace with settings
- Run `python -m compileall -q api worker`
- Produce refactor summary