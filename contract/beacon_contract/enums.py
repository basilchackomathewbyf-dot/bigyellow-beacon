"""Shared enums. JSON values are the wire format for edge, shore and web.

Changing a value here is a breaking contract change: bump CONTRACT_VERSION and tell the team.
"""
from __future__ import annotations

from enum import IntEnum, StrEnum

CONTRACT_VERSION = "1.0"


class Role(StrEnum):
    CREW = "crew"
    MASTER = "master"            # includes the Safety Officer
    SHORE_REVIEWER = "shore_reviewer"
    SHORE_ADMIN = "shore_admin"
    VESSEL = "vessel"            # edge device calling shore sync routes


class RankBand(StrEnum):
    OFFICER = "officer"
    RATING = "rating"
    CADET = "cadet"
    CREW = "crew"                # collapsed band: used when a band has < 5 people on the vessel


class Language(StrEnum):
    EN = "en"
    HI = "hi"
    TL = "tl"
    ID = "id"   # Bahasa Indonesia
    UK = "uk"
    ZH = "zh"


DEMO_UI_LANGUAGES: tuple[Language, ...] = (Language.EN, Language.HI)


class HazardType(StrEnum):
    SLIP_TRIP_FALL = "slip_trip_fall"
    FALL_FROM_HEIGHT = "fall_from_height"
    LADDER_ACCESS = "ladder_access"
    LIFTING_CRANE_OPS = "lifting_crane_ops"
    MOORING_OPS = "mooring_ops"
    MACHINERY_HYDRAULIC = "machinery_hydraulic"
    ENCLOSED_SPACE = "enclosed_space"
    FIRE_ELECTRICAL = "fire_electrical"
    CARGO_CHEMICAL = "cargo_chemical"
    STRUCK_BY_OBJECT = "struck_by_object"
    NAVIGATION = "navigation"
    OTHER = "other"


class IsmCategory(StrEnum):
    """Proposed list (pending Kundan / Captain review). Doc example uses unsafe_condition."""
    UNSAFE_ACT = "unsafe_act"
    UNSAFE_CONDITION = "unsafe_condition"
    EQUIPMENT_FAILURE = "equipment_failure"
    PROCEDURE_NOT_FOLLOWED = "procedure_not_followed"
    ENVIRONMENTAL = "environmental"
    OTHER = "other"


class Severity(IntEnum):
    NEGLIGIBLE = 1
    MINOR = 2
    MODERATE = 3
    MAJOR = 4
    CATASTROPHIC = 5


SEVERITY_RUBRIC: dict[int, str] = {
    1: "Negligible: no realistic injury or damage potential.",
    2: "Minor: could cause a first-aid injury or minor damage.",
    3: "Moderate: could cause a lost-time injury or equipment damage.",
    4: "Major: could cause serious injury, pollution or major equipment damage.",
    5: "Catastrophic: could cause a fatality, major pollution or loss of the vessel.",
}


class OnboardStatus(StrEnum):
    """Owned by the edge (Master)."""
    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ACTION_IN_PROGRESS = "ACTION_IN_PROGRESS"
    RESOLVED_ON_BOARD = "RESOLVED_ON_BOARD"


class ShoreStatus(StrEnum):
    """Owned by shore-api. QUEUED_FOR_LINK is the only value the edge sets (before first push)."""
    QUEUED_FOR_LINK = "QUEUED_FOR_LINK"
    NEW = "NEW"
    IN_REVIEW = "IN_REVIEW"
    REJECTED = "REJECTED"
    CLOSED = "CLOSED"


class RejectReason(StrEnum):
    DUPLICATE = "DUPLICATE"
    NOT_A_NEAR_MISS = "NOT_A_NEAR_MISS"
    INSUFFICIENT_INFO = "INSUFFICIENT_INFO"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class ActionType(StrEnum):
    ACK = "ack"
    ACTION = "action"
    RESOLVE = "resolve"
    NOTE = "note"


class ActorRole(StrEnum):
    MASTER = "master"
    SHORE = "shore"
    SYSTEM = "system"


class MessageSender(StrEnum):
    REPORTER = "reporter"
    MASTER = "master"
    SHORE = "shore"


class MediaKind(StrEnum):
    PHOTO = "photo"
    AUDIO = "audio"   # edge only, deleted after the reporter confirms the draft, never synced


class CheckinMode(StrEnum):
    QUICK = "quick"
    CHAT = "chat"


class CheckinTag(StrEnum):
    REST = "rest"
    WORKLOAD = "workload"
    HOME = "home"
    FAMILY = "family"
    HEALTH = "health"
    TEAM = "team"


class WelfareStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    CONTACTED = "contacted"


class LearningStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    RETRACTED = "retracted"


class LearningPriority(StrEnum):
    NORMAL = "normal"
    URGENT = "urgent"


class Audience(StrEnum):
    SAME_VESSEL = "same_vessel"
    SELECTED_VESSELS = "selected_vessels"
    ALL_VESSELS = "all_vessels"


class RankFilter(StrEnum):
    ALL = "all"
    OFFICERS = "officers"
    RATINGS = "ratings"


class LearningMediaKind(StrEnum):
    IMAGE = "image"
    GIF_MP4 = "gif_mp4"
    VIDEO = "video"


class AnchorType(StrEnum):
    MOTIVATION = "motivation"
    SAFETY = "safety"
    NEWS = "news"


class AnchorStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    RETRACTED = "retracted"


class InboxKind(StrEnum):
    SHORE_REPLY = "shore_reply"
    MASTER_REPLY = "master_reply"
    STATUS_CHANGE = "status_change"
    LEARNING = "learning"
    ANCHOR = "anchor"
    CHECKIN_REMINDER = "checkin_reminder"


class LinkStatus(StrEnum):
    UP = "UP"
    DOWN = "DOWN"
    UNKNOWN = "UNKNOWN"


class LinkOverride(StrEnum):
    AUTO = "auto"
    UP = "up"
    DOWN = "down"


class SyncEntity(StrEnum):
    TICKET = "ticket"
    TICKET_ACTION = "ticket_action"
    TICKET_MESSAGE = "ticket_message"
    LEARNING_STATS = "learning_stats"
    CHECKIN_AGGREGATE = "checkin_aggregate"
    ANCHOR_STATS = "anchor_stats"


class SyncOp(StrEnum):
    INSERT = "insert"
    UPSERT = "upsert"
    DELETE = "delete"


class PullChangeType(StrEnum):
    TICKET_SHORE_STATUS = "ticket.shore_status"
    TICKET_MESSAGE = "ticket_message"
    LEARNING_PUBLISHED = "learning.published"
    LEARNING_RETRACTED = "learning.retracted"
    FLEET_ALERT = "fleet_alert"
    RAIL_UPDATE = "rail_update"
    ANCHOR_SCHEDULED = "anchor.scheduled"
    BRIEF_ENRICHMENT = "brief_enrichment"


class SseEvent(StrEnum):
    TICKET_NEW = "ticket.new"
    TICKET_UPDATED = "ticket.updated"
    MESSAGE_NEW = "message.new"
    LEARNING_NEW = "learning.new"
    SYNC_STATUS = "sync.status"
    BRIEF_UPDATED = "brief.updated"
    ANCHOR_NEW = "anchor.new"
    CHECKIN_REMINDER = "checkin.reminder"
    WELFARE_REQUEST = "welfare.request"   # master channel only


class RailCategory(StrEnum):
    SELF_HARM = "self_harm"
    HARM_TO_OTHERS = "harm_to_others"
    ABUSE = "abuse"
    MEDICAL_EMERGENCY = "medical_emergency"
    MODEL_OUTPUT_DENY = "model_output_deny"
