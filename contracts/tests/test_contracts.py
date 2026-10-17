"""Run: pytest -q  (from beacon-ai/)"""
import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from safety.rails import SafetyRails, guarded_turn  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "schemas"


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def validator(name):
    schemas = {f.name: load(f) for f in S.glob("*.json")}
    reg = Registry().with_resources(
        [(n, Resource.from_contents(s)) for n, s in schemas.items()]
        + [(s["$id"], Resource.from_contents(s)) for s in schemas.values()]
    )
    return Draft202012Validator(schemas[name], registry=reg, format_checker=FormatChecker())


def strip_demo(rec):
    return {k: v for k, v in rec.items() if not k.startswith("_")}


# ---------- schemas ----------
@pytest.mark.parametrize("f", sorted(S.glob("*.json")), ids=lambda p: p.name)
def test_schema_is_valid(f):
    Draft202012Validator.check_schema(load(f))


def test_seed_near_misses_valid():
    v = validator("near_miss.schema.json")
    for rec in load(ROOT / "seed/demo_near_misses.json"):
        v.validate(strip_demo(rec))


def test_clarification_requires_question():
    v = validator("near_miss.schema.json")
    rec = strip_demo(load(ROOT / "seed/demo_near_misses.json")[0])
    rec["needs_clarification"] = True
    rec["clarifying_question"] = None
    assert list(v.iter_errors(rec)), "needs_clarification=true without a question must fail"


def test_unknown_hazard_rejected():
    v = validator("near_miss.schema.json")
    rec = strip_demo(load(ROOT / "seed/demo_near_misses.json")[0])
    rec["hazard_type"] = "aliens"
    assert list(v.iter_errors(rec))


def test_sync_delta_has_no_transcript_slot():
    v = validator("sync_delta.schema.json")
    nm = [strip_demo(r) for r in load(ROOT / "seed/demo_near_misses.json")]
    delta = {
        "delta_id": "11111111-2222-4333-8444-555555555555",
        "schema_version": "1.0",
        "device_ref": "dev-x",
        "vessel_id": "VSL-DEMO01",
        "seq_from": 0, "seq_to": 3,
        "created_at": "2026-10-16T06:00:00Z",
        "near_misses": nm,
        "checkin_signals": [{
            "checkin_id": "11111111-2222-4333-8444-666666666666",
            "reporter_ref": "anon-c9d0e1f2", "rank_group": "deck_rating",
            "date": "2026-10-16", "mood": 6, "fatigue": 7, "workload": 6
        }],
        "escalations": [],
    }
    v.validate(delta)
    bad = copy.deepcopy(delta)
    bad["checkin_signals"][0]["transcript"] = "anything"
    assert list(v.iter_errors(bad)), "transcript must never be accepted in a sync delta"
    print(f"\n  demo delta gz size: {len(__import__('gzip').compress(json.dumps(delta).encode()))} bytes")


# ---------- rails ----------
rails = SafetyRails()


@pytest.mark.parametrize("text,lang,cat", [
    ("I just want to die", "en", "crisis"),
    ("मैं मरना चाहता हूँ", "hi", "crisis"),
    ("he has chest pain and can't breathe", "en", "medical_emergency"),
])
def test_rail_fires(text, lang, cat):
    r = rails.check_input(text, lang)
    assert r.triggered and r.category == cat and r.stage == "pre_model"


@pytest.mark.parametrize("text", [
    "I nearly slipped on the hydraulic leak near the crane, again.",
    "Tired today, long cargo watch",
    "The old engine died at noon",   # 'died' about a machine must not fire
])
def test_rail_quiet(text):
    assert not rails.check_input(text).triggered


def test_model_not_called_on_crisis():
    called = []
    reply, r = guarded_turn(rails, "I want to die", "en", lambda t: called.append(t) or "x")
    assert r.triggered and not called and "PLACEHOLDER" in reply


def test_bad_model_output_replaced():
    reply, r = guarded_turn(rails, "feeling low", "en", lambda t: "You have depression.")
    assert r.triggered and r.stage == "post_model"


def test_hindi_fixed_response_used():
    _, r = guarded_turn(rails, "मैं मरना चाहता हूँ", "hi", lambda t: "x")
    assert "धन्यवाद" in r.fixed_response
