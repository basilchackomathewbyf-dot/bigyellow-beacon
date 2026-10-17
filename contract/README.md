# beacon_contract (v1.0, frozen)

Every payload exchanged by the crew app, the edge server, shore-api and the dashboard.

| Module | Contents |
|---|---|
| `enums.py` | Roles, rank bands, hazard types, ISM categories, severity 1–5 + rubric, ticket statuses, sync entities, pull change types, SSE event names, rail categories |
| `edge_api.py` | Crew app ↔ edge: auth, reports (draft → structure → answer → submit), tickets, messages, morning brief, check-in, mood history, learnings, Daily Anchor, inbox, sync status |
| `sync.py` | Edge ↔ shore: `SyncDelta`, `SyncEvent` (with per-entity payload validation, field ownership and forbidden-key checks), `PushResponse`, `PullChange`/`PullResponse` with typed payloads |
| `shore_api.py` | Dashboard ↔ shore: tickets, AI analysis, learnings, fleet, Daily Anchor, plus the Gemini `*LLMOutput` response schemas |
| `events.py` | SSE channels and message encoding |
| `security.py` | `reporter_ref` (per-ticket HMAC), sync request signing and verification |
| `privacy.py` | `K_ANON`, `collapse_rank_band`, `scrub_text`, forbidden sync keys |
| `fixtures.py` | The full demo scenario as valid model instances |
| `export.py` | Writes `generated/schemas/*.json` and `generated/fixtures/*.json` |

```bash
pip install -e "contract[dev]"
pytest -q contract/tests
python -m beacon_contract.export
```

Change policy: post in the team chat first, bump `CONTRACT_VERSION` for breaking changes, regenerate `generated/`, and update every consumer in the same PR.
