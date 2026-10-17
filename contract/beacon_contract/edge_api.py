"""Edge API payloads (crew app <-> edge server). Paths are in docs/TECHNICAL_DESIGN.md §12."""
from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .base import ContractModel, Id, LocalizedText, LongText, Score1to5, ShortText
from .enums import (
    ActionType, ActorRole, AnchorType, CheckinMode, CheckinTag, HazardType, InboxKind, IsmCategory,
    Language, LearningMediaKind, LearningPriority, LinkOverride, LinkStatus, MediaKind, MessageSender,
    OnboardStatus, RailCategory, RankBand, RejectReason, Role, Severity, ShoreStatus, WelfareStatus,
)

Pin = Annotated[str, Field(pattern=r"^\d{4,6}$")]
HHMM = Annotated[str, Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]

# ---------------------------------------------------------------- auth

class QrPayload(ContractModel):
    """Encoded in the pairing QR. One code pairs one roster member's device."""
    v: Literal[1] = 1
    edge_url: str
    vessel_id: Id
    vessel_name: str
    code: str = Field(pattern=r"^[A-Z0-9]{4}-[A-Z0-9]{4}$")
    crew_id: Id


class PairingCodeCreate(ContractModel):
    crew_id: Id


class PairingCodeResponse(ContractModel):
    code: str
    crew_id: Id
    display_name: str
    qr_payload: QrPayload
    expires_at: datetime


class PairRequest(ContractModel):
    pairing_code: str
    crew_id: Id
    pin: Pin   # set at pairing; 4 digits crew, 6 digits master (enforced by edge)


class PairResponse(ContractModel):
    device_id: Id
    device_token: str
    crew_id: Id
    role: Role
    vessel_id: Id


class LoginRequest(ContractModel):
    device_token: str
    pin: Pin


class SessionResponse(ContractModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime
    role: Role
    crew_id: Id
    vessel_id: Id


class MeResponse(ContractModel):
    crew_id: Id
    display_name: str
    role: Role
    rank: str
    rank_band: RankBand
    language: Language
    vessel_id: Id
    vessel_name: str
    checkin_reminder_at: HHMM = "18:00"


class PreferencesUpdate(ContractModel):
    language: Language | None = None
    checkin_reminder_at: HHMM | None = None


class Healthz(ContractModel):
    status: Literal["ok", "degraded"]
    edge_version: str
    models: dict[str, bool]          # {"gemma": true, "whisper": true, "embeddings": false}
    ai_mode: Literal["fake", "ollama"]


# ---------------------------------------------------------------- reports

class MediaRef(ContractModel):
    media_id: Id
    kind: MediaKind
    url: str | None = None


class DraftCreated(ContractModel):
    draft_id: Id
    media: list[MediaRef] = []


class StructuredFields(ContractModel):
    """What Gemma returns. Any field may be null ("if unsure return null, never guess")."""
    title_en: ShortText | None = None
    description_en: LongText | None = None
    location_on_board: ShortText | None = None
    hazard_type: HazardType | None = None
    ism_category: IsmCategory | None = None
    severity: Severity | None = None
    immediate_action: str | None = None
    occurred_at: datetime | None = None


class SubmittedFields(StructuredFields):
    """What the crew submits after review: the core fields become required."""
    title_en: ShortText
    description_en: LongText
    location_on_board: ShortText
    hazard_type: HazardType
    ism_category: IsmCategory
    severity: Severity


class SafetyOutcome(ContractModel):
    rail_hit: bool = False
    category: RailCategory | None = None
    fixed_message: str | None = None        # shown instead of any model output
    offer_welfare: bool = False             # app asks "Would you like the Master to check on you?"


class SimilarOpenTicket(ContractModel):
    ticket_id: Id
    ticket_no: str
    title_en: str
    similarity: float = Field(ge=0, le=1)


class StructureResponse(ContractModel):
    draft_id: Id
    original_language: Language | str
    transcript_original: str | None = None
    fields: StructuredFields
    clarifying_question: LocalizedText | None = None
    confidence: float = Field(ge=0, le=1)
    similar_open_ticket: SimilarOpenTicket | None = None   # local dedup warning (cosine > 0.85, 7 days)
    safety: SafetyOutcome = SafetyOutcome()
    prompt_version: str = "structure/v1"
    model: str = "unknown"


class DraftAnswer(ContractModel):
    answer: LongText


class ReportSubmit(ContractModel):
    draft_id: Id
    fields: SubmittedFields
    share_name_with_master: bool = False


class TicketActionCreate(ContractModel):
    text: LongText
    responsible_rank: str | None = None
    due_at: datetime | None = None
    resolve: bool = False


class TicketActionView(ContractModel):
    action_id: Id
    ticket_id: Id
    actor_role: ActorRole
    action_type: ActionType
    text: str | None = None
    responsible_rank: str | None = None
    due_at: datetime | None = None
    created_at: datetime


class CrewTicket(ContractModel):
    """GET /reports/mine item."""
    ticket_id: Id
    ticket_no: str
    title_en: str
    created_at: datetime
    severity: Severity
    hazard_type: HazardType
    onboard_status: OnboardStatus
    shore_status: ShoreStatus
    reject_reason: RejectReason | None = None
    unread_messages: int = 0


class MasterTicket(ContractModel):
    """GET /master/tickets item. reporter_name is set only when the reporter opted in."""
    ticket_id: Id
    ticket_no: str
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
    shore_status: ShoreStatus
    rank_band: RankBand
    reporter_name: str | None = None
    media: list[MediaRef] = []
    actions: list[TicketActionView] = []


class MessageCreate(ContractModel):
    body: LongText


class MessageView(ContractModel):
    message_id: Id
    ticket_id: Id
    sender: MessageSender
    body: str
    created_at: datetime
    read_at: datetime | None = None


# ---------------------------------------------------------------- master brief

class MoodTrend(ContractModel):
    k_ok: bool                       # False → n < 5, direction must be insufficient_data
    n: int
    direction: Literal["improving", "stable", "declining", "insufficient_data"]
    summary: str

    @model_validator(mode="after")
    def _k(self) -> "MoodTrend":
        if not self.k_ok and self.direction != "insufficient_data":
            raise ValueError("mood trend must be insufficient_data when k_ok is false")
        return self


class BriefHazard(ContractModel):
    ticket_id: Id
    ticket_no: str
    title_en: str
    severity: Severity
    age_hours: float


class RecommendedAction(ContractModel):
    action: ShortText
    why: str
    evidence_ticket_ids: list[Id] = Field(min_length=1)


class MorningBrief(ContractModel):
    vessel_id: Id
    brief_date: date
    headline: ShortText
    rest_risk: Literal["low", "medium", "high"]
    mood_trend: MoodTrend
    open_hazards: list[BriefHazard] = Field(default_factory=list, max_length=5)
    recommended_action: RecommendedAction
    fleet_context: str | None = None     # from shore brief_enrichment
    model: str
    prompt_version: str
    generated_at: datetime


class LearningStatsView(ContractModel):
    learning_id: Id
    title: str
    priority: LearningPriority
    crew_total: int
    delivered: int
    opened: int
    acknowledged: int
    check_correct: int


# ---------------------------------------------------------------- check-in

class CheckinStart(ContractModel):
    mode: CheckinMode
    mood: Score1to5
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    fatigue: Score1to5 | None = None
    tags: list[CheckinTag] = []

    @model_validator(mode="after")
    def _quick_complete(self) -> "CheckinStart":
        if self.mode == CheckinMode.QUICK and self.fatigue is None:
            raise ValueError("quick check-in needs fatigue")
        return self


class CheckinScores(ContractModel):
    mood: Score1to5
    fatigue: Score1to5
    workload: Score1to5 | None = None


class CheckinAfter(ContractModel):
    supportive_line: str
    tip: str


class CheckinTurnRequest(ContractModel):
    text: LongText          # audio turns are multipart with an 'audio' file instead


class CheckinTurnResponse(ContractModel):
    checkin_id: Id
    done: bool
    prompt: str | None = None            # next Gemma question when not done
    scores: CheckinScores | None = None  # when done
    after: CheckinAfter | None = None    # when done
    safety: SafetyOutcome = SafetyOutcome()


class WelfareRequestCreate(ContractModel):
    consent: Literal[True]


class WelfareRequestView(ContractModel):
    """Master sees name and time only. Never check-in text or scores."""
    welfare_id: Id
    crew_id: Id
    display_name: str
    created_at: datetime
    status: WelfareStatus


class MoodEntry(ContractModel):
    ship_date: date
    mood: Score1to5
    fatigue: Score1to5
    workload: Score1to5 | None = None
    sleep_hours: float | None = None
    tags: list[CheckinTag] = []


class MoodInsight(ContractModel):
    insight: str
    tip: str


class MoodHistory(ContractModel):
    range: Literal["7d", "30d", "90d"]
    entries: list[MoodEntry]
    streak_days: int
    top_tags: list[CheckinTag]
    insight: MoodInsight | None = None


# ---------------------------------------------------------------- daily anchor, learnings, inbox

class AnchorCardView(ContractModel):
    card_id: Id
    publish_date: date
    type: AnchorType
    title: str                   # already in the user's language
    body: str
    source_name: str | None = None
    source_url: str | None = None
    image_url: str | None = None
    is_seed: bool = False
    helpful: bool = False
    saved: bool = False


class AnchorReact(ContractModel):
    viewed: bool | None = None
    helpful: bool | None = None
    saved: bool | None = None


class CheckQuestionPublic(ContractModel):
    question: str
    options: list[str] = Field(min_length=3, max_length=3)


class LearningMediaRef(ContractModel):
    media_id: Id
    kind: LearningMediaKind
    url: str
    duration_s: float | None = None


class LearningCard(ContractModel):
    learning_id: Id
    title: str
    context: str
    situation: str
    do_points: list[str] = Field(min_length=1, max_length=5)
    dont_points: list[str] = Field(min_length=1, max_length=5)
    check_question: CheckQuestionPublic
    priority: LearningPriority
    media: list[LearningMediaRef] = []
    published_at: datetime
    opened: bool = False
    acked: bool = False


class LearningAck(ContractModel):
    opened: bool | None = None
    acked: bool | None = None
    check_answer: int | None = Field(default=None, ge=0, le=2)


class LearningAckResult(ContractModel):
    check_correct: bool | None = None


class InboxItem(ContractModel):
    inbox_id: Id
    kind: InboxKind
    ref_id: Id
    title: str
    created_at: datetime
    read_at: datetime | None = None


class SyncStatus(ContractModel):
    """GET /sync/status (fixes the truncated row in the design doc)."""
    link: LinkStatus
    override: LinkOverride
    last_probe_at: datetime | None = None
    last_push_at: datetime | None = None
    last_pull_at: datetime | None = None
    pending_events: int
    pending_media: int
    last_push_bytes_gz: int | None = None
