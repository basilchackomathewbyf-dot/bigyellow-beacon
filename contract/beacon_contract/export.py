"""Write JSON Schemas and demo fixtures for non-Python consumers (web MSW mocks, TS types).

    python -m beacon_contract.export            # writes contract/generated/{schemas,fixtures}
    npx json-schema-to-typescript ...           # or openapi-typescript against the running APIs
"""
from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

from pydantic import BaseModel

from . import edge_api, events, shore_api, sync
from .base import ContractModel
from .fixtures import ALL_FIXTURES


def all_models() -> dict[str, type[BaseModel]]:
    out: dict[str, type[BaseModel]] = {}
    for mod in (edge_api, sync, shore_api, events):
        prefix = mod.__name__.rsplit(".", 1)[-1]
        for name, obj in inspect.getmembers(mod, inspect.isclass):
            if issubclass(obj, ContractModel) and obj is not ContractModel and obj.__module__ == mod.__name__:
                out[f"{prefix}.{name}"] = obj
    return out


def main(root: str | None = None) -> None:
    base = Path(root) if root else Path(__file__).resolve().parents[1] / "generated"
    (base / "schemas").mkdir(parents=True, exist_ok=True)
    (base / "fixtures").mkdir(parents=True, exist_ok=True)
    for name, model in all_models().items():
        (base / "schemas" / f"{name}.json").write_text(json.dumps(model.model_json_schema(), indent=2))
    for name, build in ALL_FIXTURES.items():
        (base / "fixtures" / f"{name}.json").write_text(
            json.dumps(build().model_dump(mode="json"), indent=2, ensure_ascii=False))
    print(f"wrote {len(all_models())} schemas and {len(ALL_FIXTURES)} fixtures to {base}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
