"""Demo fixtures: the crane hydraulic-leak scenario from docs/TECHNICAL_DESIGN.md §18.

Every fixture is built from contract models, so it is valid by construction.
Used by: web MSW mocks, edge FakeAIGateway, shore FakeGemini, and tests.
Regenerate the JSON files with: python -m beacon_contract.export
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from . import edge_api as e
from . import shore_api as s
from . import sync as y
from .enums import (
    Audience, HazardType, IsmCategory, LearningPriority, LinkOverride, LinkStatus, OnboardStatus,
    PullChangeType, RankBand, RankFilter, Severity, ShoreStatus, SyncEntity, SyncOp,
)
from .security import reporter_ref

DEMO_VESSEL_ID = "v-0007"
DEMO_VESSEL_CODE = "0007"
DEMO_VESSEL_NAME = "MV Demo Star"
SISTER_VESSELS = {"v-0003": "MV Sister One", "v-0005": "MV Sister Two"}
DEMO_VESSEL_SECRET = "demo-vessel-secret-v-0007"   # demo only; real secret lives in edge env
DEMO_CREW_ID = "c-0007-aru"                         # synthetic reporter (AB Arun, Hindi)
DEMO_TICKET_ID = "0192f0c2-7a10-7c4e-9a51-3d0b6f8e0001"
DEMO_DRAFT_ID = "0192f0c2-79f0-7a2b-8c11-1f2e3d4c0001"
T0 = datetime(2026, 10, 18, 5, 40, tzinfo=timezone.utc)

HINDI_REPORT = "क्रेन के पास हाइड्रोलिक लीक पर मैं फिर से फिसलते-फिसलते बचा।"


def structure_response() -> e.StructureResponse:
    return e.StructureResponse(
        draft_id=DEMO_DRAFT_ID,
        original_language="hi",
        transcript_original=HINDI_REPORT,
        fields=e.StructuredFields(
            title_en="Slipped on hydraulic leak near deck crane",
            description_en="Reporter nearly slipped on hydraulic oil near the deck crane. It has happened before.",
            location_on_board=None,   # unsure → null → triggers the clarifying question
            hazard_type=HazardType.SLIP_TRIP_FALL,
            ism_category=IsmCategory.UNSAFE_CONDITION,
            severity=Severity.MODERATE,
            immediate_action=None,
        ),
        clarifying_question={"en": "Which crane, and which side of the deck?",
                             "hi": "कौन सी क्रेन, और डेक का कौन सा हिस्सा?"},
        confidence=0.82,
        prompt_version="structure/v1",
        model="gemma3n:e4b",
    )


def structure_after_answer() -> e.StructureResponse:
    r = structure_response()
    return r.model_copy(update={
        "fields": r.fields.model_copy(update={"location_on_board": "Main deck, crane no. 2, starboard"}),
        "clarifying_question": None,
        "confidence": 0.9,
    })


def report_submit() -> e.ReportSubmit:
    f = structure_after_answer().fields
    return e.ReportSubmit(
        draft_id=DEMO_DRAFT_ID,
        fields=e.SubmittedFields(**f.model_dump()),
        share_name_with_master=False,
    )


def master_ticket() -> e.MasterTicket:
    f = report_submit().fields
    return e.MasterTicket(
        ticket_id=DEMO_TICKET_ID, ticket_no=f"BCN-{DEMO_VESSEL_CODE}-0012",
        title_en=f.title_en, description_en=f.description_en, description_original=HINDI_REPORT,
        original_language="hi", location_on_board=f.location_on_board, hazard_type=f.hazard_type,
        ism_category=f.ism_category, severity=f.severity, created_at=T0,
        onboard_status=OnboardStatus.NEW, shore_status=ShoreStatus.QUEUED_FOR_LINK,
        rank_band=RankBand.RATING, reporter_name=None,
    )


def morning_brief() -> e.MorningBrief:
    return e.MorningBrief(
        vessel_id=DEMO_VESSEL_ID, brief_date=date(2026, 10, 18),
        headline="Recurring hydraulic leak at crane 2 is the top risk today",
        rest_risk="medium",
        mood_trend=e.MoodTrend(k_ok=True, n=9, direction="declining",
                               summary="Fatigue has risen for 3 days among those who checked in."),
        open_hazards=[e.BriefHazard(ticket_id=DEMO_TICKET_ID, ticket_no=f"BCN-{DEMO_VESSEL_CODE}-0012",
                                    title_en="Slipped on hydraulic leak near deck crane",
                                    severity=Severity.MODERATE, age_hours=1.5)],
        recommended_action=e.RecommendedAction(
            action="Isolate crane 2, clean the deck and fit a drip tray before cargo ops",
            why="Repeat report of oil on deck at the same crane; slip injuries are the top cause in the corpus.",
            evidence_ticket_ids=[DEMO_TICKET_ID]),
        fleet_context="Two sister vessels reported crane hydraulic leaks this week; one past case led to a fractured wrist.",
        model="gemma3n:e4b", prompt_version="brief/v1", generated_at=T0,
    )


def sync_status(link: LinkStatus = LinkStatus.DOWN) -> e.SyncStatus:
    return e.SyncStatus(link=link, override=LinkOverride.AUTO, last_probe_at=T0,
                        pending_events=3, pending_media=1, last_push_bytes_gz=None)


def sync_delta() -> y.SyncDelta:
    f = report_submit().fields
    owned = y.TicketEdgeFields(
        ticket_no=f"BCN-{DEMO_VESSEL_CODE}-0012", vessel_id=DEMO_VESSEL_ID,
        reporter_ref=reporter_ref(DEMO_VESSEL_SECRET, DEMO_CREW_ID, DEMO_TICKET_ID),
        rank_band=RankBand.RATING, title_en=f.title_en, description_en=f.description_en,
        description_original=HINDI_REPORT, original_language="hi",
        location_on_board=f.location_on_board, hazard_type=f.hazard_type,
        ism_category=f.ism_category, severity=f.severity, created_at=T0,
        onboard_status=OnboardStatus.ACTION_IN_PROGRESS, media_count=1,
    ).model_dump(mode="json")
    return y.SyncDelta(
        vessel_id=DEMO_VESSEL_ID, batch_id="0192f0c3-0000-7000-8000-000000000001",
        events=[
            y.SyncEvent(event_id="0192f0c3-0000-7000-8000-0000000000e1", entity=SyncEntity.TICKET,
                        op=SyncOp.INSERT, entity_id=DEMO_TICKET_ID, version=3, occurred_at=T0,
                        owned_fields=owned),
            y.SyncEvent(event_id="0192f0c3-0000-7000-8000-0000000000e2", entity=SyncEntity.TICKET_ACTION,
                        op=SyncOp.INSERT, entity_id="0192f0c3-0000-7000-8000-0000000000a1", version=1,
                        occurred_at=T0, payload=y.TicketActionPayload(
                            action_id="0192f0c3-0000-7000-8000-0000000000a1", ticket_id=DEMO_TICKET_ID,
                            actor_role="master", action_type="action",
                            text="Isolate crane 2, clean deck", responsible_rank="Bosun",
                            created_at=T0).model_dump(mode="json")),
            y.SyncEvent(event_id="0192f0c3-0000-7000-8000-0000000000e3", entity=SyncEntity.CHECKIN_AGGREGATE,
                        op=SyncOp.UPSERT, entity_id=f"{DEMO_VESSEL_ID}:2026-10-18", version=1, occurred_at=T0,
                        payload=y.CheckinAggregatePayload(vessel_id=DEMO_VESSEL_ID, date=date(2026, 10, 18),
                                                          n=9, mood_avg=3.2, fatigue_avg=3.9,
                                                          workload_avg=3.6).model_dump(mode="json")),
        ],
    )


def pull_response() -> y.PullResponse:
    learning = y.LearningPublishedChange(
        learning_id="0192f0c4-0000-7000-8000-0000000001f1",
        title="Hydraulic oil on deck: stop, isolate, clean",
        context="Crane hydraulic leaks have caused slips on three vessels this week.",
        situation="You find oil on deck near a crane pedestal during rounds.",
        do_points=["Stop crane ops and isolate the crane", "Cordon and clean the area with absorbent",
                   "Report the leak source to the engine room"],
        dont_points=["Don't walk through oil to finish a task", "Don't hose oil overboard",
                     "Don't restart the crane before the hose is checked"],
        check_question=y.CheckQuestion(question="First thing to do when you see oil near a crane?",
                                       options=["Finish the job quickly", "Stop and isolate the crane",
                                                "Wash it overboard"], correct_index=1),
        priority=LearningPriority.URGENT, rank_filter=RankFilter.ALL,
        media=[y.LearningMediaManifest(media_id="0192f0c4-0000-7000-8000-0000000001e1", kind="video",
                                       bytes=1_200_000, sha256="0" * 64, duration_s=5.0)],
        published_at=T0,
    )
    changes = [
        (PullChangeType.TICKET_SHORE_STATUS, y.TicketShoreStatusChange(
            ticket_id=DEMO_TICKET_ID, shore_status=ShoreStatus.IN_REVIEW, updated_at=T0)),
        (PullChangeType.TICKET_MESSAGE, y.ShoreMessageChange(
            message_id="0192f0c4-0000-7000-8000-0000000001d1", ticket_id=DEMO_TICKET_ID,
            reporter_ref=reporter_ref(DEMO_VESSEL_SECRET, DEMO_CREW_ID, DEMO_TICKET_ID),
            body="Thank you. Was the leak source found?", created_at=T0)),
        (PullChangeType.LEARNING_PUBLISHED, learning),
        (PullChangeType.BRIEF_ENRICHMENT, y.BriefEnrichmentChange(
            vessel_id=DEMO_VESSEL_ID, brief_date=date(2026, 10, 18),
            fleet_context="Two sister vessels reported crane hydraulic leaks this week; one past case led to a fractured wrist.",
            cluster_ids=["cl-crane-hydraulic"])),
    ]
    return y.PullResponse(
        changes=[y.PullChange(change_id=f"0192f0c5-0000-7000-8000-00000000000{i}", type=t, created_at=T0,
                              payload=p.model_dump(mode="json")) for i, (t, p) in enumerate(changes, 1)],
        next_cursor="2026-10-18T05:40:00Z#4", has_more=False,
    )


def ai_analysis() -> s.AiAnalysis:
    return s.AiAnalysis(
        analysis_id="0192f0c6-0000-7000-8000-000000000001", ticket_id=DEMO_TICKET_ID,
        model="gemini-2.5-flash", prompt_version="analysis/v1", created_at=T0,
        output=s.AnalysisLLMOutput(
            summary="A rating nearly slipped on hydraulic oil at crane 2. It is a repeat leak. "
                    "Two sister vessels reported the same pattern this week.",
            contributing_factors=["Recurring hydraulic hose leak not repaired",
                                  "No drip tray or absorbent at the crane pedestal",
                                  "Leak reported verbally, not logged"],
            ism_check=s.Check(current="unsafe_condition", suggested="unsafe_condition", agrees=True,
                              reason="The hazard is a physical condition on deck."),
            severity_check=s.Check(current="3", suggested="4", agrees=False,
                                   reason="Matched corpus case resulted in a fracture; recurrence raises likelihood."),
            corrective_actions=["Replace the weeping hose on crane 2", "Clean and cordon the area"],
            preventive_actions=["Fit drip trays at all crane pedestals", "Add hydraulic hose checks to weekly rounds"],
            corpus_match_reasons=[s.CorpusReason(case_id="SYN-ACC-001",
                                                 why="Same precursor: recurring leak at a crane pedestal led to a slip and fracture.")],
            suggest_learning=True,
        ),
        similar_tickets=[
            s.SimilarTicket(ticket_id="0192e000-0000-7000-8000-000000000301", ticket_no="BCN-0003-0041",
                            vessel_name="MV Sister One", title_en="Oil leaking again near crane 2", score=0.91),
            s.SimilarTicket(ticket_id="0192e000-0000-7000-8000-000000000501", ticket_no="BCN-0005-0017",
                            vessel_name="MV Sister Two", title_en="AB slipped at crane pedestal, no drip tray", score=0.88),
        ],
        corpus_matches=[s.CorpusMatch(case_id="SYN-ACC-001", title="Slip on oil-contaminated deck at crane pedestal",
                                      source="synthetic (MAIB-style)", score=0.84,
                                      why="Same precursor: recurring leak at a crane pedestal.")],
    )


def learning_draft() -> s.LearningDraftLLMOutput:
    p = y.LearningPublishedChange.model_validate(pull_response().changes[2].payload)
    return s.LearningDraftLLMOutput(
        title=p.title, context=p.context, situation=p.situation, do_points=p.do_points,
        dont_points=p.dont_points, check_question=p.check_question,
        tags=s.LearningTags(tool=["deck crane"], area=["main deck"], situation=["hydraulic leak"]),
        suggested_audience=Audience.ALL_VESSELS,
    )


ALL_FIXTURES = {
    "edge.structure_response": structure_response,
    "edge.structure_after_answer": structure_after_answer,
    "edge.report_submit": report_submit,
    "edge.master_ticket": master_ticket,
    "edge.morning_brief": morning_brief,
    "edge.sync_status": sync_status,
    "sync.delta": sync_delta,
    "sync.pull_response": pull_response,
    "shore.ai_analysis": ai_analysis,
    "shore.learning_draft": learning_draft,
}
