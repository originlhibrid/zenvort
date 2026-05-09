.PHONY: up down logs build worker-logs api-logs shell-api shell-worker create-key health reset-daily

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build --no-cache

worker-logs:
	docker compose logs -f worker

api-logs:
	docker compose logs -f api

shell-api:
	docker compose exec api bash

shell-worker:
	docker compose exec worker bash

create-key:
	@read -p "Name: " name; \
	read -p "Tier (free/pro/enterprise): " tier; \
	curl -s -X POST "http://localhost:8000/v1/admin/keys?admin_secret=$${ADMIN_SECRET}" \
	  -H "Content-Type: application/json" \
	  -d "{\"name\": \"$$name\", \"tier\": \"$$tier\"}" | python3 -m json.tool

health:
	curl -s http://localhost:8000/v1/health | python3 -m json.tool

reset-daily:
	curl -s -X POST "http://localhost:8000/v1/admin/reset-daily?admin_secret=$${ADMIN_SECRET}" | python3 -m json.tool
