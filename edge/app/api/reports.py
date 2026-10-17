"""Reports API — drafts → structure → answer → submit (M1)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated, Any

from beacon_contract import new_id, reporter_ref, ticket_no
from beacon_contract.edge_api import (
    CrewTicket,
    DraftAnswer,
    DraftCreated,
    MediaRef,
    ReportSubmit,
    SafetyOutcome,
    StructuredFields,
    StructureResponse,
)
from beacon_contract.enums import (
    HazardType,
    MediaKind,
    OnboardStatus,
    Severity,
    ShoreStatus,
)
from fastapi import APIRouter, Depends, File, Form, Header, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gateway import get_gateway
from app.ai.types import StructureResult
from app.auth.deps import AuthPrincipal, get_current_user
from app.config import get_settings
from app.db.models import Draft, RailHit, Ticket, TicketMedia, TicketMessage, TicketSeq
from app.db.session import get_session
from app.errors import AppError
from app.events.emit import emit_ticket_new
from app.safety.outcome import get_rails, to_safety_outcome
from app.services import idempotency as idem
from app.services.media import delete_path, save_audio, save_photo
from app.services.outbox_tickets import enqueue_ticket_insert

router = APIRouter(tags=["reports"])


def _crew_ticket(ticket: Ticket, *, unread: int = 0) -> CrewTicket:
    reject = None
    if ticket.reject_reason:
        from beacon_contract.enums import RejectReason

        try:
            reject = RejectReason(ticket.reject_reason)
        except ValueError:
            reject = None
    return CrewTicket(
        ticket_id=ticket.id,
        ticket_no=ticket.ticket_no,
        title_en=ticket.title_en,
        created_at=ticket.created_at,
        severity=Severity(ticket.severity),
        hazard_type=HazardType(ticket.hazard_type),
        onboard_status=OnboardStatus(ticket.onboard_status),
        shore_status=ShoreStatus(ticket.shore_status),
        reject_reason=reject,
        unread_messages=unread,
    )


async def _get_own_draft(
    session: AsyncSession, draft_id: str, crew_id: str
) -> Draft:
    draft = await session.get(Draft, draft_id)
    if draft is None or draft.crew_id != crew_id:
        raise AppError("not_found", "Draft not found", status_code=404)
    return draft


def _result_to_response(draft_id: str, result: StructureResult) -> StructureResponse:
    return StructureResponse(
        draft_id=draft_id,
        original_language=result.original_language,
        transcript_original=result.transcript_original,
        fields=result.fields,
        clarifying_question=result.clarifying_question,
        confidence=result.confidence,
        similar_open_ticket=None,
        safety=SafetyOutcome(),
        prompt_version=result.prompt_version,
        model=result.model,
    )


async def _bump_rail_hit(session: AsyncSession, rule_id: str) -> None:
    today = date.today()
    result = await session.execute(
        select(RailHit).where(RailHit.rule_id == rule_id, RailHit.ship_date == today)
    )
    row = result.scalar_one_or_none()
    if row is None:
        session.add(RailHit(rule_id=rule_id, ship_date=today, count=1))
    else:
        row.count += 1


@router.post("/reports/drafts", response_model=DraftCreated)
async def create_draft(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[AuthPrincipal, Depends(get_current_user)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    text: Annotated[str | None, Form()] = None,
    language: Annotated[str | None, Form()] = None,
    audio: Annotated[UploadFile | None, File()] = None,
    photos: Annotated[list[UploadFile] | None, File()] = None,
) -> DraftCreated:
    route = "POST /reports/drafts"
    replay = await idem.get_replay(
        session, key=idempotency_key, route=route, crew_id=principal.crew_id
    )
    if replay is not None:
        return DraftCreated.model_validate(replay)

    photo_files = photos or []
    if len(photo_files) > 3:
        raise AppError("validation_error", "At most 3 photos", status_code=422)

    draft_id = new_id()
    media_meta: list[dict[str, Any]] = []
    media_refs: list[MediaRef] = []

    for upload in photo_files:
        data = await upload.read()
        if not data:
            continue
        media_id, path = save_photo(data)
        media_meta.append(
            {"media_id": media_id, "kind": "photo", "path": str(path)}
        )
        media_refs.append(
            MediaRef(media_id=media_id, kind=MediaKind.PHOTO, url=f"/api/v1/media/{media_id}")
        )

    audio_path: str | None = None
    if audio is not None:
        data = await audio.read()
        if data:
            suffix = Path(audio.filename or "audio.webm").suffix or ".webm"
            _aid, apath = save_audio(data, suffix=suffix)
            audio_path = str(apath)
            # Audio is not returned as MediaRef in DraftCreated for M1 (edge-only).

    draft = Draft(
        draft_id=draft_id,
        crew_id=principal.crew_id,
        status="open",
        transcript_original=text,
        original_language=language or principal.crew.language,
        audio_path=audio_path,
        media=media_meta or None,
    )
    session.add(draft)
    body = DraftCreated(draft_id=draft_id, media=media_refs)
    await idem.store_replay(
        session,
        key=idempotency_key,
        route=route,
        crew_id=principal.crew_id,
        response=body.model_dump(mode="json"),
    )
    await session.commit()
    return body


@router.post("/reports/drafts/{draft_id}/structure", response_model=StructureResponse)
async def structure_draft(
    draft_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[AuthPrincipal, Depends(get_current_user)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> StructureResponse:
    route = f"POST /reports/drafts/{draft_id}/structure"
    replay = await idem.get_replay(
        session, key=idempotency_key, route=route, crew_id=principal.crew_id
    )
    if replay is not None:
        return StructureResponse.model_validate(replay)

    draft = await _get_own_draft(session, draft_id, principal.crew_id)
    lang = draft.original_language or principal.crew.language or "en"
    gateway = get_gateway()

    text = draft.transcript_original
    if draft.audio_path and Path(draft.audio_path).is_file():
        transcript = await gateway.transcribe(Path(draft.audio_path), lang)
        text = transcript.text
        lang = transcript.language or lang
        draft.transcript_original = text
        draft.original_language = lang

    if not text or not text.strip():
        raise AppError("validation_error", "Draft has no text or audio", status_code=422)

    rail = get_rails().check_input(text, lang)
    if rail.triggered:
        if rail.matched_rule:
            await _bump_rail_hit(session, rail.matched_rule)
        body = StructureResponse(
            draft_id=draft_id,
            original_language=lang,
            transcript_original=None,  # never return/store crisis text further
            fields=StructuredFields(),
            clarifying_question=None,
            confidence=0.0,
            safety=to_safety_outcome(rail),
            prompt_version="none",
            model="none",
        )
        await idem.store_replay(
            session,
            key=idempotency_key,
            route=route,
            crew_id=principal.crew_id,
            response=body.model_dump(mode="json"),
        )
        await session.commit()
        return body

    photo_paths: list[Path] = []
    for m in draft.media or []:
        if m.get("kind") == "photo" and m.get("path"):
            photo_paths.append(Path(m["path"]))
    captions = await gateway.caption_photos(photo_paths) if photo_paths else None
    result = await gateway.structure_report(text, lang, captions, [])
    if result.transcript_original is None:
        result.transcript_original = text

    draft.fields = result.fields.model_dump(mode="json")
    draft.clarifying_question = result.clarifying_question
    draft.confidence = result.confidence
    draft.original_language = result.original_language
    draft.transcript_original = result.transcript_original
    draft.status = "structured"

    body = _result_to_response(draft_id, result)
    await idem.store_replay(
        session,
        key=idempotency_key,
        route=route,
        crew_id=principal.crew_id,
        response=body.model_dump(mode="json"),
    )
    await session.commit()
    return body


@router.post("/reports/drafts/{draft_id}/answer", response_model=StructureResponse)
async def answer_draft(
    draft_id: str,
    body_in: DraftAnswer,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[AuthPrincipal, Depends(get_current_user)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> StructureResponse:
    route = f"POST /reports/drafts/{draft_id}/answer"
    replay = await idem.get_replay(
        session, key=idempotency_key, route=route, crew_id=principal.crew_id
    )
    if replay is not None:
        return StructureResponse.model_validate(replay)

    draft = await _get_own_draft(session, draft_id, principal.crew_id)
    lang = draft.original_language or "en"

    rail = get_rails().check_input(body_in.answer, lang)
    if rail.triggered:
        if rail.matched_rule:
            await _bump_rail_hit(session, rail.matched_rule)
        body = StructureResponse(
            draft_id=draft_id,
            original_language=lang,
            transcript_original=draft.transcript_original,
            fields=StructuredFields.model_validate(draft.fields or {}),
            clarifying_question=draft.clarifying_question,
            confidence=draft.confidence or 0.0,
            safety=to_safety_outcome(rail),
            prompt_version="none",
            model="none",
        )
        await idem.store_replay(
            session,
            key=idempotency_key,
            route=route,
            crew_id=principal.crew_id,
            response=body.model_dump(mode="json"),
        )
        await session.commit()
        return body

    if not draft.fields:
        raise AppError("validation_error", "Structure the draft first", status_code=422)

    prior = StructureResult(
        fields=StructuredFields.model_validate(draft.fields),
        clarifying_question=draft.clarifying_question,
        confidence=draft.confidence or 0.0,
        original_language=lang,
        transcript_original=draft.transcript_original,
    )
    question = ""
    if draft.clarifying_question and isinstance(draft.clarifying_question, dict):
        question = draft.clarifying_question.get("en") or next(
            iter(draft.clarifying_question.values()), ""
        )

    result = await get_gateway().answer_clarification(prior, question, body_in.answer)
    draft.fields = result.fields.model_dump(mode="json")
    draft.clarifying_question = result.clarifying_question
    draft.confidence = result.confidence
    draft.status = "answered"

    body = _result_to_response(draft_id, result)
    await idem.store_replay(
        session,
        key=idempotency_key,
        route=route,
        crew_id=principal.crew_id,
        response=body.model_dump(mode="json"),
    )
    await session.commit()
    return body


@router.post("/reports", response_model=CrewTicket)
async def submit_report(
    body_in: ReportSubmit,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[AuthPrincipal, Depends(get_current_user)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> CrewTicket:
    route = "POST /reports"
    replay = await idem.get_replay(
        session, key=idempotency_key, route=route, crew_id=principal.crew_id
    )
    if replay is not None:
        return CrewTicket.model_validate(replay)

    draft = await _get_own_draft(session, body_in.draft_id, principal.crew_id)
    settings = get_settings()
    now = datetime.now(UTC)

    # Allocate ticket_no via ticket_seq (row lock).
    seq_row = await session.get(TicketSeq, settings.vessel_id)
    if seq_row is None:
        seq_row = TicketSeq(vessel_id=settings.vessel_id, last_seq=0)
        session.add(seq_row)
        await session.flush()
    seq_row.last_seq += 1
    seq = seq_row.last_seq
    tno = ticket_no(settings.vessel_code, seq)

    ticket_id = new_id()
    ref = reporter_ref(settings.vessel_secret, principal.crew_id, ticket_id)
    fields = body_in.fields

    ticket = Ticket(
        id=ticket_id,
        ticket_no=tno,
        vessel_id=settings.vessel_id,
        reporter_ref=ref,
        reporter_crew_id=principal.crew_id,
        share_name_with_master=body_in.share_name_with_master,
        rank_band=principal.crew.rank_band,
        title_en=fields.title_en,
        description_en=fields.description_en,
        description_original=draft.transcript_original,
        original_language=draft.original_language or "en",
        location_on_board=fields.location_on_board,
        hazard_type=fields.hazard_type.value,
        ism_category=fields.ism_category.value,
        severity=int(fields.severity),
        immediate_action=fields.immediate_action,
        occurred_at=fields.occurred_at,
        onboard_status=OnboardStatus.NEW.value,
        shore_status=ShoreStatus.QUEUED_FOR_LINK.value,
        created_at=now,
        updated_at=now,
        origin="edge",
        version=1,
    )
    session.add(ticket)

    for m in draft.media or []:
        if m.get("kind") != "photo":
            continue
        session.add(
            TicketMedia(
                id=m["media_id"],
                ticket_id=ticket_id,
                kind="photo",
                local_path=m.get("path"),
                synced=False,
                created_at=now,
                updated_at=now,
                origin="edge",
                version=1,
            )
        )

    # Delete audio before commit so a failed commit can still leave audio;
    # spec: delete on submit — do it after flush, before commit.
    audio_path = draft.audio_path
    draft.audio_path = None
    draft.status = "submitted"

    await session.flush()
    await enqueue_ticket_insert(session, ticket=ticket)

    body = _crew_ticket(ticket)
    await idem.store_replay(
        session,
        key=idempotency_key,
        route=route,
        crew_id=principal.crew_id,
        response=body.model_dump(mode="json"),
    )
    await session.commit()

    emit_ticket_new(ticket=ticket, vessel_id=settings.vessel_id)

    delete_path(audio_path)
    return body


async def _unread_by_ticket(
    session: AsyncSession, ticket_ids: list[str]
) -> dict[str, int]:
    """Unread = master/shore messages with read_at IS NULL."""
    if not ticket_ids:
        return {}
    rows = (
        await session.execute(
            select(TicketMessage.ticket_id, func.count())
            .where(
                TicketMessage.ticket_id.in_(ticket_ids),
                TicketMessage.sender.in_(("master", "shore")),
                TicketMessage.read_at.is_(None),
            )
            .group_by(TicketMessage.ticket_id)
        )
    ).all()
    return {tid: int(n) for tid, n in rows}


@router.get("/reports/mine", response_model=list[CrewTicket])
async def my_reports(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[AuthPrincipal, Depends(get_current_user)],
) -> list[CrewTicket]:
    result = await session.execute(
        select(Ticket)
        .where(Ticket.reporter_crew_id == principal.crew_id)
        .order_by(Ticket.created_at.desc())
    )
    tickets = list(result.scalars().all())
    unread = await _unread_by_ticket(session, [t.id for t in tickets])
    return [_crew_ticket(t, unread=unread.get(t.id, 0)) for t in tickets]
