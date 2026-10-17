"""Map SafetyRails RailResult → contract SafetyOutcome."""

from __future__ import annotations

from beacon_contract.edge_api import SafetyOutcome
from beacon_contract.enums import RailCategory

from app.safety.rails import RailResult, SafetyRails

_rails: SafetyRails | None = None


def get_rails() -> SafetyRails:
    global _rails
    if _rails is None:
        _rails = SafetyRails()
    return _rails


def to_safety_outcome(result: RailResult) -> SafetyOutcome:
    if not result.triggered:
        return SafetyOutcome()
    category = None
    offer = False
    if result.category:
        try:
            category = RailCategory(result.category)
        except ValueError:
            category = RailCategory.MODEL_OUTPUT_DENY
        offer = category in (RailCategory.SELF_HARM, RailCategory.HARM_TO_OTHERS)
    return SafetyOutcome(
        rail_hit=True,
        category=category,
        fixed_message=result.fixed_response,
        offer_welfare=offer,
    )
