"""
Score any extractor against the gold set.

    python run_eval.py --extractor mymodule:extract

`extract(text: str, lang: str) -> dict` must return the model-owned fields
of a NearMissRecord. Prints per-field accuracy and the failures.
Target before demo: area >= 0.85, hazard_type >= 0.8, JSON valid 100% after retry.
"""
from __future__ import annotations

import argparse
import importlib
import json
from collections import Counter
from pathlib import Path

FIELDS = ["area", "hazard_type", "ism_report_type", "recurring", "needs_clarification"]


def flatten(pred: dict) -> dict:
    return {
        "area": (pred.get("location") or {}).get("area"),
        "hazard_type": pred.get("hazard_type"),
        "ism_report_type": pred.get("ism_report_type"),
        "recurring": pred.get("recurring", False),
        "needs_clarification": pred.get("needs_clarification"),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--extractor", required=True, help="module:function")
    ap.add_argument("--data", default=str(Path(__file__).with_name("near_miss_eval.jsonl")))
    args = ap.parse_args()

    mod, fn = args.extractor.split(":")
    extract = getattr(importlib.import_module(mod), fn)

    hits, n, failures = Counter(), 0, []
    for line in Path(args.data).read_text(encoding="utf-8").splitlines():
        ex = json.loads(line)
        n += 1
        try:
            pred = flatten(extract(ex["text"], ex["lang"]))
        except Exception as e:  # noqa: BLE001
            failures.append((ex["id"], "EXCEPTION", str(e)))
            continue
        for f in FIELDS:
            if pred[f] == ex["gold"][f]:
                hits[f] += 1
            else:
                failures.append((ex["id"], f, f"pred={pred[f]!r} gold={ex['gold'][f]!r}"))

    print(f"{n} examples")
    for f in FIELDS:
        print(f"  {f:22s} {hits[f] / n:.2f}")
    if failures:
        print("\nFailures:")
        for fid, field, msg in failures:
            print(f"  {fid} {field}: {msg}")


if __name__ == "__main__":
    main()
