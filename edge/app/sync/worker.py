"""Background sync worker: `python -m app.sync.worker` / `make worker`."""

from __future__ import annotations

import asyncio
import logging
import time

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import get_settings
from app.db.session import init_engine
from app.logging import setup_logging
from app.sync.cycle import reset_probe_streak, run_sync_cycle

logger = logging.getLogger("beacon.edge.sync.worker")

PROBE_INTERVAL_S = 30.0
BACKOFF_MIN_S = 5.0
BACKOFF_MAX_S = 300.0  # 5 min


async def _loop() -> None:
    settings = get_settings()
    engine = init_engine(settings.database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    reset_probe_streak()
    backoff = BACKOFF_MIN_S
    last_probe = 0.0

    logger.info(
        "worker_started shore=%s override=%s",
        settings.shore_url,
        settings.link_override,
    )

    while True:
        now = time.monotonic()
        force_probe = (now - last_probe) >= PROBE_INTERVAL_S
        try:
            async with factory() as session:
                # Ensure session type for type checkers.
                assert isinstance(session, AsyncSession)
                summary = await run_sync_cycle(
                    session, settings=settings, force_probe=force_probe
                )
            if force_probe:
                last_probe = now
            if summary.get("skipped") == "locked":
                await asyncio.sleep(1.0)
                continue
            # Success → reset backoff.
            backoff = BACKOFF_MIN_S
            logger.info("cycle_ok %s", summary)
        except Exception:
            logger.exception("cycle_failed backoff=%.0fs", backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, BACKOFF_MAX_S)
            continue

        await asyncio.sleep(backoff)


def main() -> None:
    setup_logging()
    asyncio.run(_loop())


if __name__ == "__main__":
    main()
