# Beacon POC: decisions log

`docs/TECHNICAL_DESIGN.md` (Kundan, 17 Oct 2026) is the source of truth. This file records the defaults we build with where the design doc is silent, inconsistent or still open. Each row is **built in now** so nobody waits. Rows marked **Confirm** go to Kundan; if he changes one, update this file and the affected code in the same PR.

## A. Gaps and inconsistencies in the design doc

| # | Topic | Decision we build | Status |
|---|---|---|---|
| A1 | First Master device (Master creates pairing codes, but Master also needs pairing) | `make pair-master` on the edge prints a one-time QR/code for the Master roster entry. Every other device is paired from the Master view. | Confirm |
| A2 | Rail-hit counter "added to the vessel aggregate" vs "nothing goes to shore" | Rail hits are counted **on the edge only** (rule ID + date). **Never synced.** A single hit on a 20-person ship is identifying. | Confirm |
| A3 | `ticket_media.kind = audio` listed as a "Both" table | Audio never leaves the edge and is deleted when the reporter confirms the draft. The contract rejects any `audio` key in a SyncDelta. | Built into contract |
| A4 | "clinician-approved" fixed responses (§7, §14.3) vs placeholder (Q11) | All fixed text carries `[PLACEHOLDER – pending sign-off]` in the POC. Say "placeholder" in the demo and deck. | Built in |
| A5 | `/sync/status` response is cut off in §12 | `SyncStatus` in `beacon_contract.edge_api`: link, override, last_probe_at, last_push_at, last_pull_at, pending_events, pending_media, last_push_bytes_gz | Built into contract |
| A6 | "One SQLAlchemy model package shared by edge and shore" | **Share the Pydantic contract, not the ORM.** Each tier owns its SQLAlchemy models + Alembic. Edge already has a working schema (E1/E4), and the tiers' tables differ (crew, devices, checkins are edge-only). | Confirm |
| A7 | Enum values not listed (hazard types, ISM categories) | `beacon_contract.enums`: 12 hazard types, 6 ISM categories (`unsafe_act`, `unsafe_condition`, `equipment_failure`, `procedure_not_followed`, `environmental`, `other`), severity 1–5 with a written rubric | Confirm with Kundan + Captain Prathap |
| A8 | Python 3.11 in the doc; edge E1 was built on 3.12 | Contract supports ≥ 3.11. Edge and shore run 3.12. | Built in |
| A9 | Region | **asia-southeast1** for Cloud Run, Cloud SQL, GCS and Vertex AI (as in the doc). | Built in |
| A10 | Sync request signature format ("method + path + timestamp + sha256(body)") | `METHOD\nPATH_WITH_QUERY\nTIMESTAMP\nsha256hex(body)`, HMAC-SHA256 with the vessel API key, ±300 s window. Implemented once in `beacon_contract.security`. | Built into contract |
| A11 | reporter_ref input format | `HMAC-SHA256(vessel_secret, crew_id + ":" + ticket_id)`, first 32 hex chars, prefix `rr_`. | Built into contract |
| A12 | Pairing QR content | One code per roster member: `{v, edge_url, vessel_id, vessel_name, code, crew_id}`. PIN is set at pairing (4 digits crew, 6 digits Master). | Built into contract |
| A13 | Ollama + Gemma 3n image input (doc Q9) | Day-1 test matrix (40-ai rule). If Gemma 3n images fail under Ollama, use `gemma3:4b` for photo captions only and keep Gemma 3n for text. | Sumit tests first |
| A14 | Demo UI languages (doc Q10) | UI strings **en + hi** only. Content in any language via Gemma. Other 4 languages are stretch. | Built in |

## B. Doc's own open questions: we keep the doc's defaults

| Q | Default kept |
|---|---|
| 1 | Skipped check-ins stay private |
| 2 | Every ticket auto-forwards to shore; Master cannot block |
| 3 | Master sees reporter name only if the reporter opts in per report |
| 4 | Beacon Dashboard in React, same UI kit |
| 5 | Shore DB is Cloud SQL Postgres + pgvector (replaces our earlier Firestore plan) |
| 6 | Shore can reply after Rejected/Closed |
| 7 | Learning media is uploaded only; Gemini drafts text |
| 8 | Learnings go straight to targeted crew; Master sees stats |
| 9 | See A13 |
| 10 | See A14 |
| 11 | See A4 |

## C. Changes from our earlier plan (all superseded)
- No native Android app; `mobile/` removed. Crew and Master use one React PWA served by the edge.
- No psychologist / shore escalation role. Welfare requests go to the Master on board, with consent, name only.
- Shore storage moved from Firestore to Cloud SQL Postgres + pgvector; shore auth is email + password JWT (not Firebase Auth).
- Model serving moved from HF transformers to **Ollama** (Gemma) + **faster-whisper** + **EmbeddingGemma**.
- Old `contracts/` JSON schemas are replaced by the `contract/` Pydantic package. `contracts/` stays only until the edge migration (M0) is done, then it is deleted.
- Repo layout follows design doc §17 (`contract/`, `edge/`, `shore/`, `web/apps/{crew,dashboard}`, `web/packages/ui`, `seed/`, `scripts/`).

## D. Engineering seams that let 4 people work in parallel
1. **Contract first** (`contract/`, frozen at v1.0).
2. **AI gateway interfaces** with a Fake implementation that returns contract fixtures:
   - edge: `edge/app/ai/gateway.py` → `FakeAIGateway` (Basil) and `OllamaGateway` (Sumit), switched by `BEACON_AI=fake|ollama`
   - shore: `shore/app/ai/gateway.py` → `FakeGemini` and `VertexGemini`, switched by `SHORE_AI=fake|vertex`
3. **Mock shore** on the edge side (`edge/tools/mock_shore.py`) until shore-api is deployed.
4. **MSW mocks** in the web apps from `contract/generated/fixtures/*.json`.
