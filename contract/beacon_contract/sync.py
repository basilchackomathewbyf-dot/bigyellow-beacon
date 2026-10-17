"""Edge <-> shore sync contract (docs/TECHNICAL_DESIGN.md §13.1).

Privacy is enforced here, not just documented: a SyncDelta containing any crew
identifier or transcript key fails validation on both sides.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from .base import ContractModel, Id, LocalizedText
from .enums import (
    AnchorType, CONTRACT_VERSION, HazardType, IsmCategory, LearningMediaKind, LearningPriority,
    OnboardStatus, PullChangeType, RankBand, RankFilter, RejectReason, Severity, ShoreStatus,
    SyncEntity, SyncOp,
)
from .privacy import FORBIDDEN_SYNC_KEYS, K_ANON

EDGE_OWNED_TICKET_FIELDS: frozenset[str] = frozenset({
    "ticket_no", "vessel_id", "reporter_ref", "rank_band", "title_en", "description_en",
    "description_original", "original_language", "location_on_board", "hazard_type",
    "ism_category", "severity", "immediate_action", "occurred_at", "created_at",
    "onboard_status", "media_count",
})
SHORE_OWNED_TICKET_FIELDS: frozenset[str] = frozenset({
    "shore_status", "reject_reason", "reject_note", "assigned_to",
})

MAX_EVENTS_PER_BATCH = 500
MAX_BATCH_BYTES_GZ = 256 * 1024


def _find_forbidden(obj: Any, path: str = "") -> str | None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in FORBIDDEN_SYNC_KEYS:
                return f"{path}.{k}" if path else k
            hit = _find_forbidden(v, f"{path}.{k}" if path else k)
            if hit:
                return hit
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hit = _find_forbidden(v, f"{path}[{i}]")
            if hit:
                return hit
    return None


# ---------------------------------------------------------------- typed payloads (validated per entity)

class TicketEdgeFields(ContractModel):
    ticket_no: str
    vessel_id: Id
    reporter_ref: str = Field(pattern=r"^rr_[0-9a-f]{32}$")
    rank_band: RankBand
    title_en: str
    description_en: str
    description_original: str | None = None
    original_language: str
    location_on_board: str
    hazard_type: HazardType
    ism_category: IsmCategory
    severity: Severity
    immediate_action: str | None = None
    occurred_at: datetime | None = None
    created_at: datetime
    onboard_status: OnboardStatus
    media_count: int = 0


class TicketActionPayload(ContractModel):
    action_id: Id
    ticket_id: Id
    actor_role: Literal["master"]
    action_type: Literal["ack", "action", "resolve", "note"]
    text: str | None = None
    responsible_rank: str | None = None
    due_at: datetime | None = None
    created_at: datetime


class TicketMessagePayload(ContractModel):
    message_id: Id
    ticket_id: Id
    sender: Literal["reporter", "master"]
    body: str
    created_at: datetime


class LearningStatsPayload(ContractModel):
    learning_id: Id
    vessel_id: Id
    delivered: int
    opened: int
    acknowledged: int
    check_correct: int


class CheckinAggregatePayload(ContractModel):
    vessel_id: Id
    date: date
    n: int = Field(ge=K_ANON)          # aggregates with n < 5 are never synced
    mood_avg: float = Field(ge=1, le=5)
    fatigue_avg: float = Field(ge=1, le=5)
    workload_avg: float | None = Field(default=None, ge=1, le=5)


class AnchorStatsPayload(ContractModel):
    card_id: Id
    vessel_id: Id
    views: int
    helpful: int
    saved: int


_PAYLOAD_MODELS: dict[SyncEntity, type[ContractModel]] = {
    SyncEntity.TICKET_ACTION: TicketActionPayload,
    SyncEntity.TICKET_MESSAGE: TicketMessagePayload,
    SyncEntity.LEARNING_STATS: LearningStatsPayload,
    SyncEntity.CHECKIN_AGGREGATE: CheckinAggregatePayload,
    SyncEntity.ANCHOR_STATS: AnchorStatsPayload,
}


class SyncEvent(ContractModel):
    event_id: Id
    entity: SyncEntity
    op: SyncOp
    entity_id: Id
    version: int = Field(ge=1)
    occurred_at: datetime
    owned_fields: dict[str, Any] | None = None   # ticket only: edge-owned fields
    payload: dict[str, Any] | None = None        # every other entity

    @model_validator(mode="after")
    def _validate(self) -> "SyncEvent":
        hit = _find_forbidden(self.owned_fields) or _find_forbidden(self.payload)
        if hit:
            raise ValueError(f"forbidden key in sync event: {hit}")
        if self.entity == SyncEntity.TICKET:
            if not self.owned_fields or self.payload is not None:
                raise ValueError("ticket events carry owned_fields only")
            extra = set(self.owned_fields) - EDGE_OWNED_TICKET_FIELDS
            if extra:
                raise ValueError(f"edge may not send shore-owned or unknown ticket fields: {sorted(extra)}")
            if self.op == SyncOp.INSERT:
                TicketEdgeFields.model_validate(self.owned_fields)
        else:
            if self.payload is None or self.owned_fields is not None:
                raise ValueError(f"{self.entity} events carry payload only")
            _PAYLOAD_MODELS[self.entity].model_validate(self.payload)
        return self


class SyncDelta(ContractModel):
    vessel_id: Id
    batch_id: Id
    contract_version: Literal["1.0"] = CONTRACT_VERSION  # type: ignore[assignment]
    events: list[SyncEvent] = Field(min_length=1, max_length=MAX_EVENTS_PER_BATCH)


class PushEventAck(ContractModel):
    event_id: Id
    status: Literal["applied", "duplicate", "rejected"]
    error: str | None = None


class PushResponse(ContractModel):
    batch_id: Id
    acks: list[PushEventAck]


# ---------------------------------------------------------------- pull (shore -> edge)

class TicketShoreStatusChange(ContractModel):
    ticket_id: Id
    shore_status: ShoreStatus
    reject_reason: RejectReason | None = None
    reject_note: str | None = None
    updated_at: datetime


class ShoreMessageChange(ContractModel):
    message_id: Id
    ticket_id: Id
    reporter_ref: str
    body: str
    created_at: datetime


class CheckQuestion(ContractModel):
    question: str
    options: list[str] = Field(min_length=3, max_length=3)
    correct_index: int = Field(ge=0, le=2)


class LearningMediaManifest(ContractModel):
    media_id: Id
    kind: LearningMediaKind
    bytes: int = Field(le=2 * 1024 * 1024)
    sha256: str
    duration_s: float | None = Field(default=None, le=6.0)


class LearningPublishedChange(ContractModel):
    learning_id: Id
    title: str
    context: str
    situation: str
    do_points: list[str]
    dont_points: list[str]
    check_question: CheckQuestion
    priority: LearningPriority
    rank_filter: RankFilter
    media: list[LearningMediaManifest] = []
    published_at: datetime


class LearningRetractedChange(ContractModel):
    learning_id: Id
    retracted_at: datetime


class FleetAlertChange(ContractModel):
    alert_id: Id
    title: str
    body: str
    severity: Severity
    cluster_id: Id | None = None
    created_at: datetime


class RailUpdateChange(ContractModel):
    version: str
    rules: dict[str, Any]


class AnchorScheduledChange(ContractModel):
    card_id: Id
    publish_date: date
    type: AnchorType
    title: LocalizedText
    body: LocalizedText
    source_name: str | None = None
    source_url: str | None = None
    image_media_id: Id | None = None


class BriefEnrichmentChange(ContractModel):
    vessel_id: Id
    brief_date: date
    fleet_context: str = Field(max_length=400)   # 2 to 3 lines
    cluster_ids: list[Id] = []


_CHANGE_MODELS: dict[PullChangeType, type[ContractModel]] = {
    PullChangeType.TICKET_SHORE_STATUS: TicketShoreStatusChange,
    PullChangeType.TICKET_MESSAGE: ShoreMessageChange,
    PullChangeType.LEARNING_PUBLISHED: LearningPublishedChange,
    PullChangeType.LEARNING_RETRACTED: LearningRetractedChange,
    PullChangeType.FLEET_ALERT: FleetAlertChange,
    PullChangeType.RAIL_UPDATE: RailUpdateChange,
    PullChangeType.ANCHOR_SCHEDULED: AnchorScheduledChange,
    PullChangeType.BRIEF_ENRICHMENT: BriefEnrichmentChange,
}


class PullChange(ContractModel):
    change_id: Id
    type: PullChangeType
    created_at: datetime
    payload: dict[str, Any]

    @model_validator(mode="after")
    def _typed(self) -> "PullChange":
        _CHANGE_MODELS[self.type].model_validate(self.payload)
        return self

    def typed_payload(self) -> ContractModel:
        return _CHANGE_MODELS[self.type].model_validate(self.payload)


class PullResponse(ContractModel):
    changes: list[PullChange]
    next_cursor: str
    has_more: bool


class LearningMediaUrl(ContractModel):
    media_id: Id
    url: str
    expires_at: datetime
