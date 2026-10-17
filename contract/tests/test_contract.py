"""Contract tests. Run: pip install -e "contract[dev]" && pytest -q contract/tests"""
import copy
import gzip
import json
import uuid
from datetime import date

import pytest
from pydantic import ValidationError

from beacon_contract import (
    collapse_rank_band, k_anon_ok, reporter_ref, scrub_text, sign_request, sync_headers, ticket_no,
    uuid7, verify_request,
)
from beacon_contract import edge_api as e
from beacon_contract import fixtures as fx
from beacon_contract import sync as y
from beacon_contract.enums import CheckinMode, RankBand
from beacon_contract.export import all_models, main as export_main


# ---------------------------------------------------------------- fixtures & schemas

@pytest.mark.parametrize("name", sorted(fx.ALL_FIXTURES))
def test_fixture_roundtrips(name):
    obj = fx.ALL_FIXTURES[name]()
    again = type(obj).model_validate_json(obj.model_dump_json())
    assert again == obj


def test_every_model_has_json_schema():
    models = all_models()
    assert len(models) > 40
    for name, m in models.items():
        assert m.model_json_schema()["type"] == "object", name


def test_export_writes_files(tmp_path):
    export_main(str(tmp_path))
    assert (tmp_path / "fixtures" / "sync.delta.json").exists()
    assert (tmp_path / "schemas" / "sync.SyncDelta.json").exists()


def test_unknown_fields_rejected():
    data = fx.structure_response().model_dump(mode="json")
    data["surprise"] = 1
    with pytest.raises(ValidationError):
        e.StructureResponse.model_validate(data)


# ---------------------------------------------------------------- ids

def test_uuid7_is_v7_and_time_ordered():
    a, b = uuid7(), uuid7()
    assert a.version == 7 and a.variant == uuid.RFC_4122
    assert (a.int >> 80) <= (b.int >> 80)


def test_ticket_no_format():
    assert ticket_no("0007", 12) == "BCN-0007-0012"


# ---------------------------------------------------------------- anonymity & signing

def test_reporter_ref_is_per_ticket_and_stable():
    r1 = reporter_ref("s", "crew-1", "t-1")
    assert r1 == reporter_ref("s", "crew-1", "t-1")
    assert r1 != reporter_ref("s", "crew-1", "t-2")      # unlinkable across tickets
    assert r1 != reporter_ref("other", "crew-1", "t-1")
    assert r1.startswith("rr_") and len(r1) == 35


def test_sign_and_verify():
    body = b'{"x":1}'
    sig = sign_request("key", "post", "/api/v1/sync/push", 1_000, body)
    assert verify_request("key", "POST", "/api/v1/sync/push", 1_000, body, sig, now=1_100)
    assert not verify_request("key", "POST", "/api/v1/sync/push", 1_000, body + b" ", sig, now=1_100)
    assert not verify_request("bad", "POST", "/api/v1/sync/push", 1_000, body, sig, now=1_100)
    assert not verify_request("key", "POST", "/api/v1/sync/push", 1_000, body, sig, now=1_000 + 301)


def test_sync_headers():
    h = sync_headers("v-0007", "key", "GET", "/api/v1/sync/pull?cursor=x", now=42)
    assert h["X-Vessel-Id"] == "v-0007" and h["X-Timestamp"] == "42"
    assert verify_request("key", "GET", "/api/v1/sync/pull?cursor=x", 42, b"", h["X-Signature"], now=42)


# ---------------------------------------------------------------- privacy

def test_k_anon_and_band_collapse():
    assert not k_anon_ok(4) and k_anon_ok(5)
    assert collapse_rank_band(RankBand.CADET, 2) == RankBand.CREW
    assert collapse_rank_band(RankBand.RATING, 7) == RankBand.RATING


def test_scrub_text():
    roster = ["Arun Kumar", "Maria Santos"]
    t = "Arun told maria at +91 98450 12345 or arun.k@ship.com; passport P1234567. Crane no. 2, 5 m away."
    out = scrub_text(t, roster)
    for leak in ("Arun", "maria", "98450", "@ship.com", "P1234567"):
        assert leak.lower() not in out.lower(), leak
    assert "Crane no. 2, 5 m away." in out


def test_checkin_aggregate_below_k_cannot_sync():
    with pytest.raises(ValidationError):
        y.CheckinAggregatePayload(vessel_id="v-0007", date=date(2026, 10, 18), n=4, mood_avg=3, fatigue_avg=3)


def test_mood_trend_requires_insufficient_data_when_k_fails():
    with pytest.raises(ValidationError):
        e.MoodTrend(k_ok=False, n=3, direction="declining", summary="x")


# ---------------------------------------------------------------- sync rules

def test_delta_is_small():
    raw = fx.sync_delta().model_dump_json().encode()
    assert len(gzip.compress(raw)) < 3 * 1024   # doc §15.2: 1–3 KB per ticket gzipped


@pytest.mark.parametrize("key", ["reporter_crew_id", "display_name", "transcript", "crew_id"])
def test_forbidden_keys_rejected_anywhere(key):
    data = fx.sync_delta().model_dump(mode="json")
    data["events"][1]["payload"]["nested"] = {key: "x"}
    with pytest.raises(ValidationError, match="forbidden key"):
        y.SyncDelta.model_validate(data)


def test_edge_cannot_send_shore_owned_ticket_fields():
    data = fx.sync_delta().model_dump(mode="json")
    data["events"][0]["owned_fields"]["shore_status"] = "CLOSED"
    with pytest.raises(ValidationError, match="shore-owned"):
        y.SyncDelta.model_validate(data)


def test_pull_change_payload_is_typed():
    pr = fx.pull_response()
    assert pr.changes[2].typed_payload().check_question.correct_index == 1
    bad = copy.deepcopy(pr.model_dump(mode="json"))
    bad["changes"][0]["payload"]["shore_status"] = "MAYBE"
    with pytest.raises(ValidationError):
        y.PullResponse.model_validate(bad)


def test_learning_video_over_6s_rejected():
    with pytest.raises(ValidationError):
        y.LearningMediaManifest(media_id="m", kind="video", bytes=10, sha256="0", duration_s=6.5)


# ---------------------------------------------------------------- edge api rules

def test_quick_checkin_needs_fatigue():
    with pytest.raises(ValidationError):
        e.CheckinStart(mode=CheckinMode.QUICK, mood=3)
    assert e.CheckinStart(mode=CheckinMode.CHAT, mood=3).fatigue is None


def test_submit_requires_core_fields():
    with pytest.raises(ValidationError):
        e.ReportSubmit(draft_id="d", fields=e.SubmittedFields.model_validate(fx.structure_response().fields.model_dump()))


def test_clarifying_question_needs_english():
    data = fx.structure_response().model_dump(mode="json")
    data["clarifying_question"] = {"hi": "कौन सी क्रेन?"}
    with pytest.raises(ValidationError, match="'en'"):
        e.StructureResponse.model_validate(data)


def test_fixture_json_is_utf8_hindi():
    assert "क्रेन" in json.dumps(fx.structure_response().model_dump(mode="json"), ensure_ascii=False)
