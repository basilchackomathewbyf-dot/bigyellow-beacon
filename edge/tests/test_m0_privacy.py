"""M0 privacy: k-anon, crew 403 on master routes, reporter identity gating."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from beacon_contract import new_id
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Checkin, Ticket
from app.services.master_tickets import ticket_to_master_view
from app.services.wellbeing_service import daily_k_anon


@pytest.mark.asyncio
async def test_k_anonymity_4_suppressed_5_visible(session: AsyncSession):
    today = date.today()
    # 4 distinct crew → suppressed
    for i, crew_id in enumerate(["c-0007-aru", "c-0007-ab2", "c-0007-os1", "c-0007-bos"]):
        session.add(
            Checkin(
                id=new_id(),
                crew_id=crew_id,
                ship_date=today,
                mode="quick",
                mood=3,
                fatigue=3,
                workload=3,
            )
        )
    await session.commit()
    snap4 = await daily_k_anon(session, ship_date=today)
    assert snap4["n"] == 4
    assert snap4["suppressed"] is True
    assert snap4["mood_avg"] is None
    assert snap4["k_threshold"] == 5

    # 5th crew → visible
    session.add(
        Checkin(
            id=new_id(),
            crew_id="c-0007-2of",
            ship_date=today,
            mode="quick",
            mood=5,
            fatigue=2,
            workload=2,
        )
    )
    await session.commit()
    snap5 = await daily_k_anon(session, ship_date=today)
    assert snap5["n"] == 5
    assert snap5["suppressed"] is False
    assert snap5["mood_avg"] == 3.4  # (3+3+3+3+5)/5


@pytest.mark.asyncio
async def test_crew_token_403_on_master_tickets(
    client: AsyncClient, paired_crew: dict, paired_master: dict
):
    r = await client.get("/api/v1/master/tickets", headers=paired_crew["headers"])
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"

    ok = await client.get("/api/v1/master/tickets", headers=paired_master["headers"])
    assert ok.status_code == 200
    assert ok.json() == []


@pytest.mark.asyncio
async def test_reporter_name_only_when_opted_in(session: AsyncSession):
    now = datetime.now(UTC)
    base = dict(
        ticket_no="BCN-0007-0001",
        vessel_id="v-0007",
        reporter_ref="rr_deadbeef",
        reporter_crew_id="c-0007-aru",
        rank_band="rating",
        title_en="Hydraulic leak near crane",
        description_en="Near slip on oil",
        description_original="...",
        original_language="hi",
        location_on_board="Deck crane 1",
        hazard_type="slip_trip_fall",
        ism_category="unsafe_condition",
        severity=3,
        onboard_status="NEW",
        shore_status="QUEUED_FOR_LINK",
        created_at=now,
        updated_at=now,
    )
    hidden = Ticket(id=new_id(), share_name_with_master=False, **base)
    shown = Ticket(
        id=new_id(),
        share_name_with_master=True,
        ticket_no="BCN-0007-0002",
        **{k: v for k, v in base.items() if k != "ticket_no"},
    )

    view_hidden = ticket_to_master_view(hidden, "Arun Yadav")
    assert view_hidden.reporter_name is None
    dumped = view_hidden.model_dump()
    assert "reporter_ref" not in dumped
    assert "reporter_crew_id" not in dumped

    view_shown = ticket_to_master_view(shown, "Arun Yadav")
    assert view_shown.reporter_name == "Arun Yadav"


@pytest.mark.asyncio
async def test_master_tickets_omit_identity_in_json(
    client: AsyncClient, paired_master: dict, session: AsyncSession
):
    now = datetime.now(UTC)
    session.add(
        Ticket(
            id=new_id(),
            ticket_no="BCN-0007-0099",
            vessel_id="v-0007",
            reporter_ref="rr_aabbccdd",
            reporter_crew_id="c-0007-aru",
            share_name_with_master=False,
            rank_band="rating",
            title_en="Test ticket",
            description_en="Desc",
            original_language="en",
            location_on_board="Engine room",
            hazard_type="machinery_hydraulic",
            ism_category="equipment_failure",
            severity=2,
            onboard_status="NEW",
            shore_status="QUEUED_FOR_LINK",
            created_at=now,
            updated_at=now,
        )
    )
    await session.commit()

    r = await client.get("/api/v1/master/tickets", headers=paired_master["headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body) == 1
    item = body[0]
    assert item["reporter_name"] is None
    raw = r.text
    assert "reporter_ref" not in raw
    assert "c-0007-aru" not in raw
    assert "Arun" not in raw
