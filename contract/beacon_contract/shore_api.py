"""Shore dashboard payloads (Beacon Dashboard <-> shore-api) and Gemini output schemas.

Gemini structured output: pass the *LLMOutput models' JSON schema as response_schema,
then wrap the result into the stored/served model with ids, model name and prompt_version.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from .base import ContractModel, Id, LocalizedText
from .enums import (
    AnchorStatus, AnchorType, Audience, HazardType, IsmCategory, LearningMediaKind, LearningPriority,
    LearningStatus, OnboardStatus, RankBand, RankFilter, RejectReason, Role, Severity, ShoreStatus,
)
from .sync import CheckQuestion

# ---------------------------------------------------------------- auth

class ShoreLogin(ContractModel):
    email: str
    password: str


class ShoreToken(ContractModel):
    access_token: str
    refresh_token: str
    expires_in: int
    role: Literal[Role.SHORE_REVIEWER, Role.SHORE_ADMIN]


# ---------------------------------------------------------------- tickets

class ShoreTicketListItem(ContractModel):
    ticket_id: Id
    ticket_no: str
    title_en: str
    vessel_id: Id
    vessel_name: str
    severity: Severity
    hazard_type: HazardType
    ism_category: IsmCategory
    onboard_status: OnboardStatus
    shore_status: ShoreStatus
    received_at: datetime
    similar_count: int = 0
    resolved_on_board: bool = False


class ShoreTicketDetail(ShoreTicketListItem):
    """No reporter identity of any kind beyond rank band and the opaque reporter_ref."""
    description_en: str
    description_original: str | None = None
    original_language: str
    location_on_board: str
    immediate_action: str | None = None
    occurred_at: datetime | None = None
    rank_band: RankBand
    photo_urls: list[str] = []
    timeline: list[dict] = []          # actions + status changes, chronological
    reject_reason: RejectReason | None = None
    reject_note: str | None = None
    assigned_to: str | None = None


class RejectRequest(ContractModel):
    reason: RejectReason
    note: str = Field(min_length=1, max_length=1000)


class CloseRequest(ContractModel):
    resolution_note: str = Field(min_length=1, max_length=1000)


# ---------------------------------------------------------------- AI analysis

class Check(ContractModel):
    current: str
    suggested: str
    agrees: bool
    reason: str


class CorpusReason(ContractModel):
    case_id: str
    why: str


class AnalysisLLMOutput(ContractModel):
    """response_schema for Gemini ticket analysis. Never include reporter_ref in the prompt."""
    summary: str = Field(max_length=400)                      # 3 lines
    contributing_factors: list[str] = Field(max_length=6)
    ism_check: Check
    severity_check: Check
    corrective_actions: list[str] = Field(max_length=5)
    preventive_actions: list[str] = Field(max_length=5)
    corpus_match_reasons: list[CorpusReason] = []              # only case ids given in the prompt
    suggest_learning: bool


class SimilarTicket(ContractModel):
    ticket_id: Id
    ticket_no: str
    vessel_name: str
    title_en: str
    score: float


class CorpusMatch(ContractModel):
    case_id: Id
    title: str
    source: str
    url: str | None = None
    score: float
    why: str


class AiAnalysis(ContractModel):
    analysis_id: Id
    ticket_id: Id
    model: str
    prompt_version: str
    created_at: datetime
    output: AnalysisLLMOutput
    similar_tickets: list[SimilarTicket] = []
    corpus_matches: list[CorpusMatch] = []
    ai_generated: Literal[True] = True


# ---------------------------------------------------------------- learnings

class LearningTags(ContractModel):
    tool: list[str] = []
    area: list[str] = []
    situation: list[str] = []


class LearningDraftLLMOutput(ContractModel):
    """response_schema for Gemini microlearning drafts. No reporter or vessel-identifying detail."""
    title: str = Field(max_length=80)
    context: str = Field(max_length=240)
    situation: str = Field(max_length=400)
    do_points: list[str] = Field(min_length=3, max_length=3)
    dont_points: list[str] = Field(min_length=3, max_length=3)
    check_question: CheckQuestion
    tags: LearningTags
    suggested_audience: Audience


class LearningDraftRequest(ContractModel):
    ticket_id: Id


class LearningMediaView(ContractModel):
    media_id: Id
    kind: LearningMediaKind
    url: str
    bytes: int
    duration_s: float | None = None


class Learning(ContractModel):
    learning_id: Id
    source_ticket_id: Id | None = None
    title: str
    context: str
    situation: str
    do_points: list[str]
    dont_points: list[str]
    check_question: CheckQuestion
    tags: LearningTags
    priority: LearningPriority = LearningPriority.NORMAL
    audience: Audience = Audience.SAME_VESSEL
    vessel_ids: list[Id] = []
    rank_filter: RankFilter = RankFilter.ALL
    status: LearningStatus = LearningStatus.DRAFT
    ai_drafted_fields: list[str] = []
    media: list[LearningMediaView] = []
    published_at: datetime | None = None


class LearningPatch(ContractModel):
    title: str | None = None
    context: str | None = None
    situation: str | None = None
    do_points: list[str] | None = None
    dont_points: list[str] | None = None
    check_question: CheckQuestion | None = None
    tags: LearningTags | None = None
    priority: LearningPriority | None = None
    audience: Audience | None = None
    vessel_ids: list[Id] | None = None
    rank_filter: RankFilter | None = None


class LearningListItem(ContractModel):
    learning_id: Id
    title: str
    source_ticket_id: Id | None = None
    audience: Audience
    status: LearningStatus
    published_at: datetime | None = None
    vessels_delivered: int
    vessels_total: int
    ack_rate: float | None = None


# ---------------------------------------------------------------- fleet

class HazardCluster(ContractModel):
    cluster_id: Id
    label: str
    hazard_type: HazardType | None = None
    ticket_ids: list[Id]
    vessel_ids: list[Id]
    size: int


class VesselWellbeingTile(ContractModel):
    vessel_id: Id
    vessel_name: str
    k_ok: bool
    n: int | None = None
    mood_avg: float | None = None
    fatigue_avg: float | None = None


class FleetOverview(ContractModel):
    open_by_severity: dict[int, int]
    tickets_per_vessel_30d: dict[str, int]
    top_hazard_types: list[tuple[HazardType, int]]
    learnings_ack_rate: float | None = None
    clusters: list[HazardCluster] = []
    wellbeing: list[VesselWellbeingTile] = []


class Vessel(ContractModel):
    vessel_id: Id
    name: str
    code: str
    imo: str | None = None
    type: str
    fleet_group: str
    last_sync_at: datetime | None = None


# ---------------------------------------------------------------- daily anchor

class NewsItem(ContractModel):
    source_name: str
    url: str | None = None
    title: str | None = None
    text: str | None = None


class DraftWeekRequest(ContractModel):
    start_date: date
    mix: dict[AnchorType, int] = {AnchorType.MOTIVATION: 3, AnchorType.SAFETY: 3, AnchorType.NEWS: 1}
    news_items: list[NewsItem] = []


class AnchorDraftLLMOutput(ContractModel):
    type: AnchorType
    title: str = Field(max_length=80)
    body: str = Field(max_length=400)
    source_name: str | None = None
    source_url: str | None = None


class AnchorCard(ContractModel):
    card_id: Id
    publish_date: date
    type: AnchorType
    title: LocalizedText
    body: LocalizedText
    source_name: str | None = None
    source_url: str | None = None
    image_uri: str | None = None
    audience: Literal["all"] | list[Id] = "all"
    status: AnchorStatus = AnchorStatus.DRAFT
    ai_drafted: bool = False
    is_seed: bool = False
