"""Print a one-time pairing code + terminal QR for the first Master on the roster.

Usage: make pair-master
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.auth.jwt_secret import require_jwt_secret
from app.auth.pairing import build_qr_payload, create_pairing_code
from app.config import get_settings
from app.db.models import Crew
from app.db.session import get_engine, init_engine


def _first_master_crew_id(roster_path: Path) -> str | None:
    data = json.loads(roster_path.read_text(encoding="utf-8"))
    for member in data.get("crew", []):
        if member.get("is_master"):
            return member["crew_id"]
    return None


async def main() -> int:
    settings = get_settings()
    require_jwt_secret(settings)
    init_engine(settings.database_url)
    factory = async_sessionmaker(get_engine(), expire_on_commit=False)

    master_id = _first_master_crew_id(Path(settings.roster_file))
    if not master_id:
        print("No is_master crew in roster file.", file=sys.stderr)
        return 1

    async with factory() as session:
        crew = await session.get(Crew, master_id)
        if crew is None:
            print(f"Master {master_id} not in DB. Run `make seed` first.", file=sys.stderr)
            return 1
        plaintext, row = await create_pairing_code(session, master_id)
        await session.commit()
        qr = build_qr_payload(code=plaintext, crew_id=master_id)

    pair_url = f"{settings.public_edge_url.rstrip('/')}/pair"
    print(f"Master pairing code: {plaintext}")
    print(f"crew_id:            {master_id}")
    print(f"display_name:       {crew.display_name}")
    print(f"expires_at:         {row.expires_at.isoformat()}")
    print(f"URL:                {pair_url}")
    print(f"QR JSON:            {qr.model_dump_json()}")
    print()

    try:
        import qrcode
    except ImportError:
        print("(Install qrcode for terminal QR: pip install 'qrcode[pil]')")
        return 0

    qr_img = qrcode.QRCode(border=1)
    qr_img.add_data(qr.model_dump_json())
    qr_img.make(fit=True)
    qr_img.print_ascii(invert=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
