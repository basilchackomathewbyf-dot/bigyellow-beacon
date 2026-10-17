# Codex prompt: BigYellow Beacon, Crew Mobile App (Android)

> Paste everything below this line into Codex, or save it as `AGENTS.md` at the root of the `mobile/android/` repo so Codex reads it on every task.

---

## 1. What you are building

You are building the **crew mobile app** for **BigYellow Beacon**, an offline-first AI copilot for seafarers' wellbeing and safety. It is a hackathon prototype (Google Cloud AI Builder Cup 2026) that must work reliably in a live demo.

Seafarers on merchant ships usually have **no internet**. The ship has a local Wi-Fi/LAN and an on-board **edge server** ("Beacon Edge") that runs the AI (Gemma 3n) offline. **This app talks ONLY to the edge server over ship Wi-Fi. It never talks to the internet, Firebase or any cloud service.**

The app does four things for a crew member:

1. **Report a hazard / near-miss** by voice, photo or text, in their own language (Hindi, Tagalog, English for the demo). The edge server's AI turns it into a structured safety report. The crew member reviews and confirms it.
2. **Daily 60-second wellbeing check-in**, a short conversation (voice or text) in their language. Only scores leave the phone; the conversation transcript stays on the phone.
3. **See notices** from the Master / Safety Officer, automatically translated into their language, and see what happened to their own reports.
4. **Ask for help** privately ("I want to talk to someone"), which reaches the shore psychology team at the next sync.

Users: ship crew (ratings, officers, cadets, catering). Many are tired, wear gloves, are on a moving ship, have limited English, and are suspicious of anything that might report on them. Design for that.

## 2. Hard rules (do not break these)

1. **No internet dependency.** Every feature works on ship Wi-Fi with no internet. No Firebase, Google Play Services cloud APIs, analytics, crash reporting, remote fonts or remote images.
2. **Never collect crew names, crew IDs, phone numbers or emails.** The device gets a pseudonymous `reporter_ref` (e.g. `anon-c9d0e1f2`) from the edge server at pairing.
3. **Check-in transcripts never leave the phone after the turn is processed.** Store them only in the local encrypted database. Never log them (no `Log.d` with user text, ever, including in debug builds).
4. **Safety responses come from the server and are shown exactly as received.** When a response has `safety.rail_triggered = true`, show `fixed_response` on the dedicated Safety screen and do not show any AI-generated text for that turn. Never modify, shorten or translate that text in the app.
5. **Nothing is lost.** If the edge server is unreachable, save the action locally and send it later automatically. The crew member must always see "Saved on your phone, will send when connected to the ship server".
6. Location permission is never requested. Strip EXIF GPS from photos.

## 3. Tech stack

- **Kotlin**, **Jetpack Compose**, **Material 3**, single-activity, **Navigation Compose**
- MVVM: `ViewModel` + `StateFlow`, repository layer, Kotlin coroutines
- **Hilt** for DI
- **Retrofit + OkHttp + kotlinx.serialization** for HTTP
- **Room** for local storage, encrypted with **SQLCipher** (`net.zetetic:sqlcipher-android`); key stored via Android Keystore
- **WorkManager** for the offline send queue
- **DataStore (Preferences)** for settings and pairing info
- **ML Kit Barcode Scanning, bundled model** (`com.google.mlkit:barcode-scanning`, not the Play Services one) for QR pairing; it must work offline
- **CameraX** or `ActivityResultContracts.TakePicture` for photos
- `MediaRecorder` for voice recording
- Android `TextToSpeech` for reading check-in replies aloud (optional toggle)
- minSdk 26, targetSdk 35, compileSdk 35
- Package name: `ai.bigyellowfish.beacon.crew`

## 4. Connecting to the edge server (important networking details)

### 4.1 Pairing by QR

On the ship, the Master's dashboard shows a QR code. Its content is JSON:

```json
{
  "v": 1,
  "edge": "http://192.168.1.10:8080",
  "vessel_id": "VSL-DEMO01",
  "vessel_name": "MV Demo Star",
  "join_code": "7Q4K-9XPL"
}
```

The app scans it, calls `POST /api/v1/auth/pair`, then stores `edge` base URL, `device_token`, `reporter_ref`, `vessel_id`, `vessel_name` in DataStore. Also allow **manual entry** of edge URL and join code (for the demo, in case the camera fails).

### 4.2 Wi-Fi without internet (must handle)

Ship Wi-Fi has **no internet**, so Android marks it "No internet" and may route traffic to mobile data, especially in the demo, where the phone has a SIM. You must:

- Use `ConnectivityManager.requestNetwork()` with `NetworkCapabilities.TRANSPORT_WIFI` and **without** `NET_CAPABILITY_VALIDATED` / `NET_CAPABILITY_INTERNET` requirements.
- Build the OkHttp client with that `Network`'s `socketFactory` (`network.socketFactory`) so edge calls always go over Wi-Fi. Re-create the client when the Wi-Fi network changes.
- WorkManager constraints: do **not** use `NetworkType.CONNECTED` (it may require validation). Run the worker with no network constraint and check edge reachability inside the worker (`GET /health`); return `Result.retry()` with exponential backoff (start 15 s, max 5 min) if unreachable.

### 4.3 Cleartext HTTP on the LAN

The edge server uses plain HTTP on a private IP for the hackathon. Add `res/xml/network_security_config.xml` that allows cleartext **only** for private ranges / the configured edge host (add `192.168.0.0/16`-style hosts used in the demo: `192.168.1.10`, `10.0.2.2` for the emulator, `localhost`). Keep cleartext disabled for everything else. Leave a `TODO` for HTTPS with a pinned self-signed cert.

### 4.4 Connection status

While the app is in the foreground, poll `GET /api/v1/health` every 15 s (and immediately on resume or network change). Show a status chip at the top of Home:

| State | Chip text (localised) | Colour |
|---|---|---|
| Edge reachable, `model_ready = true` | "Connected to ship server" | green |
| Edge reachable, `model_ready = false` | "AI is starting up, please wait" | amber |
| Edge unreachable | "Not connected, your reports are saved on this phone" | grey |

Also show the count of pending items ("2 waiting to send").

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

## 6. Local data (Room + SQLCipher)

Tables (suggested):

- `pending_ops`: `id`, `client_id`, `type` (`near_miss_submit | near_miss_clarify | near_miss_confirm | checkin_quick | notice_ack | help`), `payload_json`, `file_paths_json`, `created_at`, `attempts`, `last_error`, `state` (`queued | sending | failed_permanent`)
- `my_reports`: local mirror of `GET /crew/near-miss` plus local-only drafts not yet sent (`record_id` nullable, `client_id`, local media paths, `summary_local`, `status`, `synced_to_shore`)
- `checkin_local`: `checkin_id` (nullable until server answers), `session_id`, `created_at`, `lang`, `scores_json`, `transcript_json` (**never sent anywhere**)
- `notices`: cached notices + `acked`

Rules:
- Media files (audio, photos) live in `filesDir/pending/` and are deleted after a confirmed successful upload.
- `PendingOpsWorker` (WorkManager unique work `beacon-sync`, `ExistingWorkPolicy.KEEP`) sends ops **in creation order**. `near_miss_confirm` must wait until its `near_miss_submit` has a `record_id`.
- Enqueue the worker on: any new op, app start, Wi-Fi network available callback, and health check turning green.
- Offline near-miss flow: when the edge is unreachable, save the raw report (audio/photo/text) as a local draft with status "Waiting for ship server". When it is sent and the AI draft comes back, notify the crew member ("Your report is ready to review") with a local notification and let them review/confirm.

## 7. Screens

Design for gloves, motion, sunlight and night watch: **minimum touch target 56 dp**, primary buttons full-width and **at least 64 dp tall**, body text ≥ 16 sp, high contrast, icons always paired with words. Support light and dark theme; follow the system setting. Accent colour: BYF signal yellow `#F2B530` on dark, `#A86F00` on light, navy ink `#14202E`. Keep text short. All strings in `strings.xml` with translations in `values-hi` and `values-fil` (Tagalog/Filipino; send `tl` to the API). Use per-app language (`AppCompatDelegate.setApplicationLocales`).

### 7.1 Welcome and language
- First launch only. Big language buttons: **हिन्दी**, **Tagalog**, **English**.
- Then a **privacy screen** in plain words (localised):
  - "Beacon does not ask your name."
  - "Your check-in conversation stays on this phone. Only scores are shared, and the Master only sees groups of 5 or more people."
  - "Safety reports go to the Master and the company safety team, without your name."
  - Button: "I understand".

### 7.2 Pairing
- "Scan the QR code from the ship's Beacon screen" with camera view (ML Kit bundled).
- Optional rank group picker (with "Prefer not to say").
- "Enter manually" link: edge URL + join code.
- On success: "Connected to MV Demo Star" → Home.

### 7.3 Home
- Top: vessel name, connection chip (4.4), pending count.
- Two huge buttons: **⚠ Report a hazard** (yellow, primary) and **🙂 Daily check-in** (shows "Done today ✓" after one).
- Below: latest 1–2 notices (urgent ones highlighted), "My reports" with status counts.
- Bottom nav: Home · My reports · Notices · Me.
- Persistent but discreet **"Need help?"** button.

### 7.4 Report a hazard: capture
- Three options as big tiles: **Speak**, **Photo**, **Type**. They can be combined (voice + photo).
- **Speak**: tap to start, tap to stop (not hold-to-talk; gloves). Show timer and live level meter; auto-stop at 60 s. Record AAC/m4a 16 kHz mono via `MediaRecorder`. Allow playback and re-record.
- **Photo**: up to 4; downscale to max 1600 px long edge, JPEG quality 80, strip EXIF (especially GPS).
- **Type**: multiline text field, keyboard in the chosen language.
- Optional "When did it happen?" chips: Just now / Earlier today / Yesterday.
- **Send** button. While waiting: progress screen "Beacon is reading your report…" with an animated indicator. It can take up to 40 s; show a cancel option that keeps the report saved locally.
- If the edge is unreachable: save locally, show "Saved on your phone. It will be sent when you are connected to the ship server." → back to Home.

### 7.5 Report a hazard: review
- Card showing (localised `display` labels): **Where**, **What**, **How serious** (colour pill: low/medium/high/critical), **Happened before?**, and the summary sentence in their language. Collapsible "What you said" showing `original_text`.
- If `needs_clarification`: show `question_local` prominently with answer by voice or text → `/clarify` → refreshed card.
- Each field tappable to correct it via a simple picker (area list, hazard list, severity). Changes go in `edits` on confirm.
- Buttons: **Confirm and send** (primary), "Discard".
- After confirm: "Thank you. Your report helps keep everyone safe." Status: "Sent to the Master ✓" and later "Shared with the company ✓" when `synced_to_shore` becomes true.

### 7.6 My reports
- List: summary, area/hazard labels, date, status pill (Open / Action assigned / Closed), sync icon (on phone / on ship server / shared with company).
- Detail: the Master's action in their language when available.
- Pull to refresh; local drafts awaiting review appear at top with "Review now".

### 7.7 Daily check-in
- Chat-style screen, max 4 AI turns, aimed at ~60 seconds. Header: "1 minute check-in · only scores leave your phone".
- Each turn: big mic button (tap to start/stop) **and** a text field. Show the AI reply as a chat bubble; optional speaker button reads it aloud with `TextToSpeech` in the crew's language (if a voice is installed; hide the button if not).
- After `done` or turn 4 → call `/finish` → summary screen: three simple meters (Mood, Energy = 10 − fatigue, Workload) and the server's `message`. Link: "See my trend".
- **Offline / model loading fallback**: show the **Quick check-in**: three large sliders with emoji anchors (Mood, Tiredness, Workload) + "Hours of sleep" stepper → queued `POST /crew/checkin/quick`. No free text in the quick check-in.

### 7.8 Me
- My trend (30 days) as a simple line chart (draw with Compose Canvas; no chart library needed): mood, fatigue, workload.
- Language, rank group, voice replies on/off, privacy explanation, "Delete my check-in history on this phone", "Unpair this phone".

### 7.9 Safety screen (rail triggered)
- Calm full screen, no AI text. Shows `fixed_response` exactly as received.
- If `ask_consent`: two clear buttons, "Yes, someone can contact me" / "Not now". Send the answer: for check-in, via `/finish` `consent_to_contact`; for near-miss safety holds, via `POST /crew/help` with `category: talk_to_someone`.
- Always show: "If you are in danger now, tell the officer on watch or the Master."
- No "back to chat" for this session; button "Return home".

### 7.10 Need help
- Three options: "I want to talk to someone", "Medical problem", "Something else".
- Contact channel choice (in-app chat / satellite call / through the Master).
- Explain: "This goes to the company's support team at the next connection. It does not go to the Master unless you choose that."
- Works offline (queued). Shows "Request saved, will be sent".

## 8. Project structure

```
mobile/android/
├── AGENTS.md                      # this prompt
├── app/src/main/
│   ├── AndroidManifest.xml
│   ├── res/xml/network_security_config.xml
│   ├── res/values/strings.xml, values-hi/, values-fil/
│   └── java/ai/bigyellowfish/beacon/crew/
│       ├── BeaconApp.kt                     # Hilt application, WorkManager config
│       ├── MainActivity.kt
│       ├── di/                              # NetworkModule, DbModule, RepoModule
│       ├── data/
│       │   ├── remote/
│       │   │   ├── EdgeApi.kt               # Retrofit interface (section 5)
│       │   │   ├── dto/                     # @Serializable DTOs, 1:1 with section 5
│       │   │   ├── FakeEdgeApi.kt           # canned responses (section 9)
│       │   │   └── WifiNetworkBinder.kt     # section 4.2
│       │   ├── local/                       # Room DB, DAOs, entities, SQLCipher factory
│       │   ├── prefs/PairingStore.kt        # DataStore
│       │   ├── repo/                        # NearMissRepo, CheckinRepo, NoticeRepo, HelpRepo, HealthRepo
│       │   └── sync/PendingOpsWorker.kt
│       ├── media/                           # AudioRecorder, PhotoProcessor (resize + EXIF strip), Tts
│       ├── ui/
│       │   ├── theme/                       # colours, type, big-target components
│       │   ├── components/                  # ConnectionChip, BigButton, SeverityPill, MicButton, ChatBubble
│       │   ├── onboarding/                  # Welcome, Privacy, Pairing (+ QR scanner)
│       │   ├── home/
│       │   ├── report/                      # Capture, Waiting, Review, Clarify
│       │   ├── reports/                     # list + detail
│       │   ├── checkin/                     # Chat, Summary, QuickCheckin
│       │   ├── notices/
│       │   ├── me/                          # Trend chart, settings
│       │   ├── safety/SafetyScreen.kt
│       │   └── help/
│       └── nav/BeaconNavGraph.kt
└── app/src/test/ and androidTest/
```

## 9. Demo mode (so the app can be built before the edge server is ready)

- Add a debug-only setting **"Use demo server (fake)"**. When on, `FakeEdgeApi` replaces the real one and returns the JSON examples from section 5 with a 3-second delay for near-miss and 1 second for check-in turns.
- FakeEdgeApi triggers the safety path when the text contains `TEST_RAIL` (so the Safety screen can be demoed without real crisis phrases).
- FakeEdgeApi `health` can be toggled between green / amber / unreachable from the debug menu to show offline behaviour.
- Default edge URL for the emulator: `http://10.0.2.2:8080`.

## 10. Build order (do these in order; each must compile and run)

1. **M1 Skeleton**: project, theme, navigation, Hilt, DataStore, strings in 3 languages, Welcome → Privacy → Pairing (manual entry) → Home with fake data.
2. **M2 Networking**: `EdgeApi`, DTOs, Wi-Fi binding, health polling + connection chip, FakeEdgeApi, pairing via API.
3. **M3 Near-miss online**: capture (voice, photo, text) → upload → waiting → review → clarify → confirm. My reports list.
4. **M4 Offline queue**: Room + SQLCipher, `pending_ops`, `PendingOpsWorker`, local drafts, "ready to review" notification.
5. **M5 Check-in**: chat flow with voice/text, local encrypted transcript, summary, quick check-in fallback, Safety screen.
6. **M6 Rest**: notices + ack, help flow, Me (trend chart, settings, delete history, unpair), QR scanning with ML Kit bundled.
7. **M7 Polish**: accessibility labels, large-font check, dark mode, empty/error states, unit tests.

## 11. Tests

- Unit: DTO (de)serialisation against every JSON example in section 5; `PendingOpsWorker` ordering (confirm waits for submit) and 409 handling; photo processor removes GPS EXIF; safety response always routes to Safety screen.
- Instrumented (smoke): pairing (manual) → report by text → review → confirm using FakeEdgeApi.
- A `lint` check or test that fails if any `Log.*` call receives transcript/report text (simple: wrap logging in a `SafeLog` that only accepts non-user strings, and forbid `android.util.Log` elsewhere).

## 12. Acceptance criteria (the live demo)

1. Phone in **airplane mode with only ship Wi-Fi on** (edge server on a laptop at `192.168.1.10:8080`), SIM present.
2. Pair by scanning the QR from the ship dashboard.
3. Tap **Report a hazard → Speak**, say in Hindi: *"क्रेन के पास हाइड्रोलिक लीक पर मैं फिर से फिसलते-फिसलते बचा"*, take one photo, Send.
4. Within ~40 s the review card shows Crane area · Slip/fall · High · Happened before ✓ in Hindi, plus a clarifying question; answer it by voice; confirm.
5. My reports shows it as "Sent to the Master ✓".
6. Stop the edge server: chip turns grey; file a text report; it shows "Saved on your phone". Start the edge server again: it sends automatically within a minute and a "ready to review" notification appears.
7. Do a check-in in Hindi in under 90 s; summary shows three meters. Confirm the transcript is not in any network request except the per-turn upload (check with OkHttp logging **disabled for bodies** in release; in debug, log only URLs and status codes).
8. Typing `TEST_RAIL` in demo mode opens the Safety screen with the fixed response and consent buttons.

## 13. Out of scope (do not build)

iOS, login/passwords, push notifications from the cloud, Firebase, in-app chat with the psych team (just queue the request), on-phone LLM, maps, location, analytics.

When something in this spec is ambiguous, choose the option that **works offline, collects less personal data, and is simpler to demo**, and leave a `// DECISION:` comment explaining it.
