# Beacon POC: hackathon build plan (Google Cloud AI Builder Cup 2026)

Source of truth: `docs/TECHNICAL_DESIGN.md`. Defaults for open points: `docs/DECISIONS.md`.

## 1. What wins this

Judges see a 3-minute video/demo and skim the repo. They reward a real problem, a clear "wow", and serious use of Google AI and Google Cloud. Our story:

> **A seafarer in the middle of the ocean, with no internet, reports a hazard by voice in Hindi. Gemma on the ship understands it and alerts the Master in one second. When the satellite link returns, 2 KB reaches shore, Gemini links it to the same hazard on two sister ships and a past accident, and a 6-second microlearning goes back to the whole fleet.**

Five moments the demo must land, in order:
1. **Airplane mode + Hindi voice → structured English report** (Gemma 3n, offline)
2. **Master's tablet buzzes within a second** (SSE on the ship LAN)
3. **Link up → "2.1 KB synced"** on screen (edge → Cloud Run)
4. **Gemini analysis**: two similar tickets on sister vessels + matched accident case, with citations (Vertex AI + Cloud SQL pgvector)
5. **Microlearning published to all vessels → appears on the crew phone + anonymous reply in the inbox** (shore → ship)

Privacy is the trust story: identity and audio never leave the ship, per-ticket HMAC pseudonyms, k ≥ 5, transcripts never stored. Show it, briefly.

### Google tech we must visibly use (put this table in the README and deck)
| Google product | Where | What it does in the demo |
|---|---|---|
| **Gemma 3n** (via Ollama) | Edge | Structures, translates, asks the clarifying question, check-in, morning brief, offline |
| **EmbeddingGemma** | Edge | Local "similar report already open" warning |
| **Gemini on Vertex AI** | Shore | Ticket analysis, cluster labels, microlearning draft, brief enrichment, Daily Anchor drafts |
| **Vertex AI text embeddings** | Shore | Similar tickets across the fleet + accident-corpus match |
| **Cloud Run** | Shore | shore-api + dashboard |
| **Cloud SQL for PostgreSQL + pgvector** | Shore | Tickets, learnings, embeddings |
| **Cloud Storage** | Shore | Photos and learning media, signed URLs |

## 2. Scope tiers (cut from the bottom when time runs out)

| Tier | Features | Rule |
|---|---|---|
| **P0: the demo** | Pairing + PIN · Hindi voice/photo/text report → Gemma draft → clarify → submit (anonymous) · SSE Master alert · Master ack + action · outbox + sync push/pull + link toggle + KB counter · shore ticket queue + detail · Gemini analysis with similar tickets + corpus match · Accept / Reject · anonymous reply both ways · microlearning: Gemini draft → edit → **image or ≤6 s video upload** → publish → arrives on board → crew ack · crew inbox + My reports with both statuses · HTTPS (mkcert) on demo phones | Must work 5 times in a row before anything in P1 starts |
| **P1: strong extras** | Quick check-in + 30-day mood chart · Daily Anchor today card (seed pack) · morning brief with fleet_context · Master learning read rates · welfare request flow · fleet overview cards · local dedup warning | Build after P0 rehearsal passes |
| **P2: stretch** | Chat check-in + Gemma mood insight · Daily Anchor studio + Gemini week draft + translation · HDBSCAN clusters (use simple similarity grouping before this) · GIF→MP4 · learning retract · rank filters · 6 UI languages · audit log UI | Only if P0 + P1 are rehearsed |

## 3. Team and ownership

| Engineer (doc §17) | Person | Owns | Folder |
|---|---|---|---|
| 1. Edge platform | **Basil** | contract, edge API, SSE, outbox + sync worker, mock shore, Docker, mkcert, demo scripts | `contract/`, `edge/` (not `edge/app/ai`, `edge/app/safety`), `scripts/` |
| 2. AI | **Sumit** | Ollama + whisper + EmbeddingGemma, safety rails, all edge prompts, check-in, brief; Gemini prompts + gateway on shore | `edge/app/ai/`, `edge/app/safety/`, `edge/prompts/`, `shore/app/ai/`, `shore/prompts/` |
| 3. Crew app | **Amar** | React PWA (crew + Master views), service worker, Dexie outbox, voice/photo capture, SSE, i18n | `web/apps/crew/`, `web/packages/ui/` |
| 4. Shore | **Engineer 4** (assign) | shore-api, Cloud SQL, GCS, media transcoding, Cloud Run deploy, Beacon Dashboard | `shore/` (not `shore/app/ai`), `web/apps/dashboard/` |
| Lead | Kundan | Design decisions (DECISIONS.md "Confirm" rows), demo script, deck | |

Everyone builds against **fakes first** (DECISIONS.md §D), so nobody waits for anyone.

## 4. Phases and checkpoints

Times are working hours from when the update is applied. Each checkpoint has an exit test; don't move on until it passes.

### Phase 0: freeze (1 h, everyone)
- Basil: finish the E4 test fix, commit, apply this update (`scripts/apply_update.sh`), push to `develop`.
- Everyone: pull, read `TECHNICAL_DESIGN.md` §1, §5, §9, §18 and `DECISIONS.md`. Send the "Confirm" rows to Kundan.
- Engineer 4: **start Cloud SQL creation now** (takes 10–15 min; commands in `20-shore.mdc` §2).
- Sumit: pull Ollama models now (several GB; commands in `40-ai.mdc` §2).
- Amar: `mkcert` on the edge laptop + install the root CA on the demo phones (`30-web.mdc` §1). Do this first: mic, camera and service workers need HTTPS.
- **Exit:** `pytest -q contract/tests` passes on every laptop; Cloud SQL instance creating; models downloading.

### Phase 1: build against fakes (4–5 h, parallel)
| Who | Milestones |
|---|---|
| Basil | **M0** migrate edge to the contract + new schema + roster/PIN auth · **M1** reports API with FakeAIGateway · **M2** master board + actions + SSE · **M3** messages + inbox |
| Sumit | **A1** model test matrix (Gemma text/image, whisper Hindi) · **A2** structure pipeline + eval ≥ 80% on hazard_type · **A3** safety rails |
| Amar | **W1** shell, auth, i18n, MSW mocks · **W2** crew report flow with voice/photo/text + Dexie outbox · **W3** Master board + SSE alert |
| Eng 4 | **S1** shore-api on Cloud Run + Cloud SQL + JWT · **S2** sync push/pull with HMAC · **D1** dashboard queue + detail |
- **Checkpoint 1 (end of phase):** phone (real HTTPS) → report with fake AI → Master tablet buzzes → ack shows on the phone.

### Phase 2: wire the real pieces (3–4 h)
| Who | Milestones |
|---|---|
| Basil | **M4** outbox + sync worker against mock shore, then real shore-api · link override + `/sync/status` with bytes |
| Sumit | **A4** swap `BEACON_AI=ollama` in the edge · **A5** Gemini analysis + embeddings + corpus match on shore |
| Amar | **W4** inbox, messages, My reports with both statuses, sync banner + link toggle in Master view |
| Eng 4 | **S3** tickets accept/reject/close/messages · **S4** analysis job on arrival · **D2** analysis pane, accept/reject, reply |
- **Checkpoint 2:** demo steps 1–5 of `TECHNICAL_DESIGN.md` §18 with real Gemma and real Gemini.

### Phase 3: the learning loop (2–3 h)
| Who | Milestones |
|---|---|
| Eng 4 | **S5** learnings CRUD, media upload (image + ≤6 s video with ffprobe), publish → pull changes · **D3** microlearning studio |
| Sumit | **A6** Gemini microlearning draft + brief enrichment |
| Basil | **M5** learnings pull + media fetch + feed/ack/stats APIs |
| Amar | **W5** learnings feed + card + ack, urgent learning alert on Master |
- **Checkpoint 3:** full demo steps 1–7.

### Phase 4: P1 extras (2–3 h, only after Checkpoint 3 passes twice)
Check-in quick mode + mood history (Sumit + Basil + Amar) · Daily Anchor today card from seed pack · morning brief with fleet context · welfare request · fleet overview cards.

### Phase 5: demo hardening (2 h, everyone; non-negotiable)
- `scripts/demo_reset.sh`: wipe edge + shore demo data, reseed, set link DOWN. One command.
- Pre-warm Ollama (`keep_alive`) so the first Hindi report isn't slow; Cloud Run `--min-instances 1`.
- Rehearse the 8 steps **5 times**. Time each step. Fix only what breaks.
- **Record the backup demo video** (screen + phone camera) after the first clean run. Submit this even if live works.
- Freeze `develop`, merge to `main`, tag `v0.1-demo`.

### Phase 6: submission (1–2 h, Basil + Kundan)
See §6 checklist.

## 5. Risks and mitigations

| Risk | Mitigation |
|---|---|
| HTTPS on phones fails → no mic, no offline | Phase 0 mkcert first; Chrome flag fallback; `<input capture>` fallback for audio/photo |
| Gemma 3n image input not available in Ollama | A13: `gemma3:4b` for captions only |
| Gemma slow on the demo laptop | Use E2B if needed; `keep_alive`; short prompts; one few-shot example; show the "reading your report…" state |
| Hindi speech accuracy | whisper `small`; seed the exact demo sentence in the eval set; clarifying question covers gaps |
| Cloud SQL / Vertex setup delays | Start in Phase 0; FakeGemini + mock shore keep everyone unblocked |
| Venue Wi-Fi | Travel router with no uplink for the ship LAN; laptop's own uplink = "VSAT"; `BEACON_LINK_OVERRIDE` toggle |
| RAM on the edge laptop (Ollama + whisper + Postgres + Docker) | Run Postgres in Docker, Ollama native; close everything else; test the full stack together in Phase 2 |
| Scope creep | Tiers in §2. P1 starts only after Checkpoint 3 passes twice |
| Merge conflicts | Folder ownership in §3; contract changes only via Basil |

## 6. Submission checklist
- [ ] Repo README: problem, solution, architecture image (`docs/design-media/media/image1.png`), **Google tech table**, how to run edge/shore/web, demo credentials, team
- [ ] 3-minute demo video (follows §1's five moments, with captions)
- [ ] Deck: problem (numbers), solution, live loop, architecture, Google tech, privacy by design, impact, roadmap
- [ ] Repo access for judges (public or shared, per Hack2skill rules); **secrets check** before going public; BYF approval
- [ ] Only synthetic data in `seed/`; fixed safety text marked placeholder
- [ ] Cloud Run URL working on submission day (min instances 1)
- [ ] Tag `v0.1-demo`

## 7. Daily rhythm
- Stand-up at each checkpoint (10 min): what works end-to-end, what's blocked, what to cut.
- Every merge to `develop` keeps `pytest` green in `contract/`, `edge/`, `shore/`.
- Anyone touching `contract/` posts in the team chat first.
