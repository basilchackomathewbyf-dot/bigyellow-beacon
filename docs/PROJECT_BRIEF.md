# BigYellow Beacon: teammate onboarding brief

> Share this with anyone joining. It is also a good first message to paste into your AI coding tool.

## What we're building (60 seconds)
Beacon is an **offline-first AI copilot for seafarer safety and wellbeing**, for the **Google Cloud AI Builder Cup 2026**.

- On a ship with no internet, a crew member opens the **Beacon web app** on their phone (served by an **edge server** on the ship's Wi-Fi) and reports a near-miss **by voice, photo or text in their own language**.
- **Gemma** on the edge turns it into a structured English report and asks one clarifying question if needed.
- The **Master** (same web app, Master view) gets an **instant alert**, acknowledges, and acts on board.
- When the satellite link returns, a **~2 KB sync** reaches **shore on Google Cloud**. In the **Beacon Dashboard**, **Gemini** analyses the ticket, finds the same hazard on sister vessels and in past accidents. A reviewer accepts, **replies anonymously** to the reporter, and publishes a **microlearning** (text + image or ≤ 6 s video) back to one, some or all vessels.
- Extras: daily wellbeing check-in with private mood history, Daily Anchor card, Master's morning brief.

**Privacy is core:** crew identity, audio and transcripts never leave the ship; shore sees a per-ticket pseudonym; wellbeing numbers only for groups of 5+.

## Users
| User | App | Login |
|---|---|---|
| Crew | Beacon web app (phone), crew view | Scan QR + 4-digit PIN |
| Master / Safety Officer | Beacon web app (tablet/laptop), Master view | Scan QR + 6-digit PIN |
| Shore reviewer / admin | Beacon Dashboard | Email + password |

No native mobile app. No psychologist role.

## Read these, in order
1. `docs/TECHNICAL_DESIGN.md`: the design (Kundan). §1, §5, §9, §18 first.
2. `docs/DECISIONS.md`: defaults where the design is open.
3. `docs/PLAN.md`: scope tiers (P0 first), owners, phases, checkpoints.
4. Your rule file in `.cursor/rules/`: `10-edge` (Basil), `40-ai` (Sumit), `30-web` (Amar: crew app; Engineer 4: dashboard), `20-shore` (Engineer 4).
5. `contract/README.md`: every payload is defined there. Don't redefine shapes; import them (Python) or generate types from `contract/generated/schemas` (TypeScript).

## Getting started
```bash
gh repo clone <owner>/bigyellow-beacon && cd bigyellow-beacon && git checkout develop
python3 -m venv .venv && source .venv/bin/activate && pip install -e "contract[dev]" && pytest -q contract/tests
open -a Cursor .
```
In Cursor Agent: `@<your rule>.mdc Build milestone <first ID> exactly as specified.`
Build against the fakes (Fake AI gateway, mock shore, MSW mocks) so you never wait for someone else.

## Team rules
- `git pull` before work; after a milestone: `git add . && git commit -m "<ID>: …" && git pull && git push` (branch `develop`).
- Stay in your folders (`docs/PLAN.md` §3). Contract changes only after posting in the team chat.
- P0 first. Nothing from P1 until the full demo passes twice.
- Questions: Basil (build), Kundan (design).
