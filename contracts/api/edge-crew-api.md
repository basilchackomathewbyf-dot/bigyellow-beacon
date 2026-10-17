## 5. API contract (edge server, base `{edge}/api/v1`)

All requests except pairing and health send:
- `Authorization: Bearer {device_token}`
- `X-Client-Version: 0.1.0`
- `Accept-Language: {app language}` (`hi`, `tl`, `en`)

All write requests include a client-generated `client_id` (UUID v4) for **idempotency**. If the server returns `409 duplicate_client_id`, treat it as success and use the returned body.

Error format:
```json
{ "error": { "code": "model_loading", "message": "Model is loading" } }
```
| HTTP | code | App behaviour |
|---|---|---|
| 401 | `invalid_token` | Clear pairing, go to Pairing screen |
| 409 | `duplicate_client_id` | Treat as success |
| 422 | `validation_error` | Show message, keep user input |
| 503 | `model_loading` | Keep item queued, show amber chip, retry |
| 5xx / timeout | — | Queue locally, retry |

Timeouts: connect 5 s, read **90 s** (AI inference on audio + photo can take 20–40 s), write 60 s.

### 5.1 Auth and system

**`POST /auth/pair`**
```json
// request
{ "join_code": "7Q4K-9XPL", "vessel_id": "VSL-DEMO01", "device_label": "Pixel 7", "language": "hi", "rank_group": "deck_rating" }
// response 200
{ "device_token": "eyJ...", "reporter_ref": "anon-c9d0e1f2", "vessel_id": "VSL-DEMO01", "vessel_name": "MV Demo Star", "edge_version": "0.1.0" }
```
`rank_group` is optional, one of `deck_officer | engine_officer | deck_rating | engine_rating | catering | cadet | undisclosed` (default `undisclosed`). Explain in the UI that it is used only for group statistics.

**`GET /health`** (no auth)
```json
{ "status": "ok", "model_ready": true, "shore_link": "down", "edge_time": "2026-10-17T05:40:00Z" }
```

### 5.2 Near-miss reports

**`POST /crew/near-miss`**, `multipart/form-data`

| Part | Type | Required |
|---|---|---|
| `client_id` | text (UUID) | yes |
| `lang` | text (`hi`/`tl`/`en`) | yes |
| `source` | text: `voice` / `photo` / `text` / `voice+photo` | yes |
| `text` | text | if no audio |
| `occurred_at` | ISO-8601 | no |
| `audio` | file `audio/mp4` (.m4a, AAC, 16 kHz mono, ≤ 60 s) | if voice |
| `photos` | 0–4 files `image/jpeg` | no |

Response 200 (normal):
```json
{
  "record_id": "6f1d2c1e-8a2b-4c3d-9e4f-0a1b2c3d4e03",
  "status": "draft",
  "draft": {
    "original_language": "hi",
    "original_text": "क्रेन के पास हाइड्रोलिक लीक पर मैं फिर से फिसलते-फिसलते बचा।",
    "english_text": "I nearly slipped on the hydraulic leak near the crane, again.",
    "location": { "area": "crane_area", "detail": null },
    "hazard_type": "slip_trip_fall",
    "ism_report_type": "near_miss",
    "severity": { "level": "high", "potential_consequence": "serious_injury" },
    "recurring": true,
    "description": "Crew member nearly slipped on a recurring hydraulic oil leak in the crane area.",
    "display": {
      "area_label": "क्रेन क्षेत्र",
      "hazard_label": "फिसलना / गिरना",
      "severity_label": "उच्च",
      "summary_local": "क्रेन के पास बार-बार होने वाले तेल रिसाव पर फिसलने से बचे।"
    }
  },
  "needs_clarification": true,
  "clarifying_question": {
    "field": "location",
    "question_en": "Which crane, and which side of the deck?",
    "question_local": "कौन सी क्रेन, और डेक का कौन सा हिस्सा?"
  },
  "safety": { "rail_triggered": false }
}
```
The `display` block holds labels already translated to the crew's language. Show those, not the enum values.

Response 200 when a safety rail fires:
```json
{
  "record_id": null,
  "status": "safety_hold",
  "safety": {
    "rail_triggered": true,
    "category": "crisis",
    "fixed_response": "[PLACEHOLDER – pending clinician review] Thank you for telling me...",
    "ask_consent": true
  }
}
```
→ Navigate to the **Safety screen** (section 7.9).

**`POST /crew/near-miss/{record_id}/clarify`**, multipart: `client_id`, `answer_text` or `audio`. Response has the same shape as above (updated draft, maybe another question; max 2 clarifications, then the server stops asking).

**`POST /crew/near-miss/{record_id}/confirm`**
```json
// request (edits optional: only fields the crew changed in the review screen)
{ "client_id": "…", "edits": { "location.area": "crane_area", "location.detail": "crane no. 1, starboard", "severity.level": "high" } }
// response
{ "record_id": "…", "status": "confirmed", "synced_to_shore": false }
```

**`GET /crew/near-miss?since={iso}`**
```json
{ "items": [
  { "record_id": "…", "created_at": "…", "summary_local": "…", "area_label": "…", "hazard_label": "…",
    "status": "open", "master_action_local": null, "synced_to_shore": true }
] }
```
`status`: `open | action_assigned | closed`. `master_action_local` is the Master's corrective action, translated.

### 5.3 Wellbeing check-in

**`POST /crew/checkin/start`**
```json
// request
{ "client_id": "…", "lang": "hi" }
// response
{ "session_id": "…", "turn": 1, "max_turns": 4,
  "reply": { "text": "सुप्रभात! आज आप कैसा महसूस कर रहे हैं?" } }
```

**`POST /crew/checkin/{session_id}/turn`**, multipart: `client_id`, `text` or `audio` (m4a)
```json
// response normal
{ "turn": 2, "done": false,
  "user_text": "थका हुआ हूँ, सिर्फ़ 4 घंटे सोया।",
  "reply": { "text": "समझ गया। आज काम का बोझ कैसा है?" },
  "safety": { "rail_triggered": false } }
// response when rail fires
{ "turn": 2, "done": true, "user_text": "…",
  "safety": { "rail_triggered": true, "category": "crisis", "fixed_response": "…", "ask_consent": true } }
```
`user_text` is the server's transcription of what the crew said. Store `user_text` and `reply.text` **only locally** (encrypted) as the transcript. The server does not keep them.

**`POST /crew/checkin/{session_id}/finish`**
```json
// request
{ "client_id": "…", "consent_to_contact": null }
// response
{ "checkin_id": "…", "scores": { "mood": 5, "fatigue": 7, "workload": 6, "sleep_hours_reported": 4 },
  "themes": ["sleep", "workload"], "message": "धन्यवाद। अपना ख्याल रखें।" }
```
`consent_to_contact` is `true/false` only if the Safety screen asked; otherwise `null`.

**`POST /crew/checkin/quick`** is the **offline fallback** (no AI). It is queued when the edge server is unreachable or the model is loading:
```json
{ "client_id": "…", "lang": "hi", "created_at": "…", "mood": 6, "fatigue": 7, "workload": 5, "sleep_hours_reported": 5 }
// response
{ "checkin_id": "…" }
```

### 5.4 History, notices, help

**`GET /crew/history?days=30`**
```json
{ "points": [ { "date": "2026-10-16", "mood": 6, "fatigue": 7, "workload": 6 } ] }
```

**`GET /crew/notices?since={iso}`**
```json
{ "items": [ { "notice_id": "…", "created_at": "…", "from_role": "master", "priority": "urgent",
  "title_local": "क्रेन क्षेत्र में सावधानी", "body_local": "…", "original_language": "en" } ] }
```
**`POST /crew/notices/{notice_id}/ack`** body `{ "client_id": "…" }`

**`POST /crew/help`**
```json
// request
{ "client_id": "…", "category": "talk_to_someone", "message": null, "consent_to_contact": true, "contact_channel": "in_app_chat" }
// response
{ "escalation_id": "…", "status": "queued_for_shore", "expected": "next_sync" }
```
`category`: `talk_to_someone | medical | other`. `contact_channel`: `in_app_chat | satellite_call | via_master`. For `medical`, show "Tell the officer on watch now" prominently; the edge also alerts the Master.

