# BigYellow Beacon

Offline-first AI copilot for seafarers' wellbeing and safety. Google Cloud AI Builder Cup 2026.

| Part | Folder | Built with | Spec |
|---|---|---|---|
| Shared contracts | `contracts/` | — | schemas, API contract, safety rails, prompts, eval, seed |
| Edge server (ship) | `edge/` | Cursor | `.cursor/rules/10-edge.mdc` |
| Shore API (GCP) | `shore/` | Cursor | `.cursor/rules/20-shore.mdc` |
| Ship + shore dashboards | `dashboards/` | Cursor | `.cursor/rules/30-dashboards.mdc` |
| Crew Android app | `mobile/android/` | Codex | `mobile/android/AGENTS.md` |
| Architecture | `docs/architecture.html` | — | open in a browser |

## Using this in Cursor

1. Open the **repo root** (`bigyellow-beacon/`) in Cursor, not a subfolder, so the rules in `.cursor/rules/` load.
2. `00-beacon-shared.mdc` is always on. The component rules attach automatically once files exist in their folder; for the first prompt in an empty folder, mention the rule with `@`.
3. Use **Agent** mode. Work one milestone per chat, review the diff, run it, commit, then start the next milestone in a new chat.
4. Never let an agent edit `contracts/` silently. If a change is needed, ask for it explicitly and tell the team.

### Kick-off prompts (paste into Cursor Agent)

**Edge, first chat**
```
@10-edge.mdc @00-beacon-shared.mdc
Build milestone E1 of the edge server exactly as specified. Create edge/ with docker-compose (db + api only for now), config, logging, health, Alembic with all tables from §4, staff PIN login, device pairing + QR payload, /me, and `make seed`. Include tests. When done, list the commands to run it and what you verified.
```
Then: `Build milestone E2 …`, `E3 …`, and so on in new chats. For E3 add: `Run make eval and show the accuracy table.`

**Shore, first chat**
```
@20-shore.mdc @00-beacon-shared.mdc
Build milestone S1 of the shore API exactly as specified: skeleton, config, Firestore async client, health, vessel API keys, scripts/create_vessel.py, Dockerfile that includes contracts/, and the deploy target for project byf-beacon-2026. Include tests with the in-memory repos. Then give me the exact gcloud commands to enable APIs, create the service account with roles, and deploy.
```
For S3 add: `The demo cluster test in §11 must pass.`

**Dashboards, first chat**
```
@30-dashboards.mdc @00-beacon-shared.mdc
Build milestone D1: the pnpm workspace, packages/ui with tokens (light + dark) and the shared components, and MSW mocks with fixtures for both apps using the example JSON from 10-edge.mdc §8/§10 and 20-shore.mdc §8, including the 3-vessel crane cluster. Self-host fonts. No CDN URLs anywhere.
```

**Useful follow-ups**
- `Check this module against the spec section §X and list every mismatch before changing anything.`
- `Write the tests from §12 for what exists so far and make them pass.`
- `Run the app and walk through the demo checklist in §14; fix what fails.`

## Who builds what (suggested)

| Person | Today |
|---|---|
| Sumit | `edge/model-server` (E2) and `edge/app/ai/*` (E3) |
| Amar | `mobile/android` in Codex (M1–M5), then ship-web D2 |
| Basil | `edge` E1/E4/E5, `shore` S1–S4, shore-web D3 |

## Integration contracts (do not drift)
- Crew app ↔ edge: `contracts/api/edge-crew-api.md`
- Edge ↔ shore: `.cursor/rules/20-shore.mdc` §5
- Ship dashboard ↔ edge: `.cursor/rules/10-edge.mdc` §8 and §10
- Shore dashboard ↔ shore: `.cursor/rules/20-shore.mdc` §8
- Data shapes: `contracts/schemas/*.json`

Run `pytest -q contracts/tests` after any change to `contracts/`.
