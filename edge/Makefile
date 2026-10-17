.PHONY: up down seed test migrate install pair-master mock-shore

# Local / no-Docker: export BEACON_DATABASE_URL=postgresql+asyncpg://beacon:beacon@localhost:5433/beacon

install:
	pip install -e ".[dev]"
	pip install -e ../contract
	pip install "qrcode[pil]"

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

pair-master:
	python -m app.pair_master

test:
	pytest -q

mock-shore:
	@echo "M4: python -m app.tools.mock_shore (not yet)"

# Placeholders for later milestones
fetch-models:
	@echo "A1: ollama pull + model_check (see 40-ai.mdc)"

eval:
	@echo "A2: edge/eval (not yet)"
