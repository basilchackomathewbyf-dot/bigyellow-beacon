FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY alembic.ini ./
COPY app ./app
COPY entrypoint.sh ./
RUN pip install --no-cache-dir -e . \
    && chmod +x /app/entrypoint.sh

# Contracts and ship-web are mounted or copied at runtime; placeholders for image layout.
RUN mkdir -p /app/contracts /app/ship-web /data /app/seed_docs
COPY seed_docs ./seed_docs

ENV BEACON_DATA_DIR=/data \
    BEACON_SHIP_WEB_DIST=/app/ship-web \
    BEACON_CONTRACTS_DIR=/app/contracts

EXPOSE 8080

ENTRYPOINT ["/app/entrypoint.sh"]
