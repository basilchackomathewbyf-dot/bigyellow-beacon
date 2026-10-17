.PHONY: up down seed test migrate fetch-models eval install

# Local / no-Docker: export BEACON_DATABASE_URL=postgresql+asyncpg://beacon:beacon@localhost:5433/beacon

install:
	pip install -e ".[dev]"

up:
	docker compose up -d --build db
	@echo "Waiting for db..."
	@sleep 3
	docker compose up -d --build api

down:
	docker compose down

migrate:
	alembic upgrade head

seed: migrate
	python -m app.seed

test:
	pytest -q

# Placeholders for later milestones
fetch-models:
	@echo "E2: run python -m model_server.fetch_models (not yet wired)"

eval:
	@echo "E3: run contracts/eval/run_eval.py against extract.near_miss"
