.PHONY: up down seed test migrate install pair-master mock-shore worker run fmt

# Settings load from edge/.env automatically (see app/config.py). No need to source .env.

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

run:
	.venv/bin/uvicorn app.main:app --port 8080 --reload

test:
	.venv/bin/pytest -q

fmt:
	.venv/bin/ruff format .
	.venv/bin/ruff check --fix . || true

mock-shore:
	BEACON_SHORE_API_KEY=$${BEACON_SHORE_API_KEY:-demo-shore-api-key} \
		.venv/bin/python tools/mock_shore.py

worker:
	.venv/bin/python -m app.sync.worker

# Placeholders for later milestones
fetch-models:
	@echo "A1: ollama pull + model_check (see 40-ai.mdc)"

eval:
	@echo "A2: edge/eval (not yet)"
