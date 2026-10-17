"""Server-Sent Events on the edge (GET /api/v1/events). Event names are in enums.SseEvent."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .base import ContractModel, Id
from .enums import HazardType, OnboardStatus, Severity, SseEvent, ShoreStatus


def master_channel(vessel_id: str) -> str:
    return f"vessel:{vessel_id}:master"


def crew_channel(crew_id: str) -> str:
    return f"crew:{crew_id}"


def vessel_channel(vessel_id: str) -> str:
    return f"vessel:{vessel_id}:all"


class SseMessage(ContractModel):
    """Wire format: `id: <id>\\nevent: <event>\\ndata: <json>\\n\\n`. Clients resume with Last-Event-ID."""
    id: Id
    event: SseEvent
    data: dict[str, Any]

    def encode(self) -> str:
        import json
        return f"id: {self.id}\nevent: {self.event.value}\ndata: {json.dumps(self.data, default=str)}\n\n"


class TicketNewData(ContractModel):
    """Master channel. Triggers banner + sound + vibration on the Master view."""
    ticket_id: Id
    ticket_no: str
    title_en: str
    severity: Severity
    hazard_type: HazardType
    location_on_board: str
    created_at: datetime


class TicketUpdatedData(ContractModel):
    ticket_id: Id
    ticket_no: str
    onboard_status: OnboardStatus
    shore_status: ShoreStatus


class WelfareRequestData(ContractModel):
    """Master channel only. Name and time; never check-in content."""
    welfare_id: Id
    display_name: str
    created_at: datetime
