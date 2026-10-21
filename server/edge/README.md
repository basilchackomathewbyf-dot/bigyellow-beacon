# BigYellow Beacon – Edge Server (`bigyellow-beacon-edge`)

Autonomous Shipboard Safety & Wellbeing Intelligence Server operating on vessel mini-PCs or Jetson devices with zero persistent internet requirement.

## Features
- **Offline-First Resilience**: Full local CRUD for near-miss reports, hazard drafts, daily wellbeing check-ins, and safety learnings even during prolonged satellite blackouts.
- **Store-and-Forward Outbox**: Critical updates are queued in `outbox` table and synced over satellite links using exponential backoff, burst-sync detection, and HMAC-SHA256 signature verification.
- **Privacy & GDPR Art. 9 Enforcement**: Personal check-in transcripts live in volatile memory only and are never stored in the database. Near-miss submissions undergo client-side and server-side PII scrubbing (`[crew]` replacements and EXIF GPS stripping).
- **Crew Device Pairing & Argon2 PINs**: Onboard device pairing via Master code, Argon2 PIN authentication (4 digits for crew, 6 digits for Master), and automatic 15-minute lockouts after 5 failed attempts.
- **Real-Time Bridge SSE Stream**: Bridge Officers & Masters receive live SSE notifications for near-miss reports, welfare alerts, and sync status without browser polling.

## Quick Start

### 1. Environment Configuration
```bash
cp .env.example .env
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Seed Database
```bash
python scripts/seed_edge_db.py
```

### 4. Run Development Server
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Swagger UI documentation will be live at: **http://127.0.0.1:8000/docs**

### 5. Run Tests
```bash
pytest -v tests/
```

## AI Setup (GCP VM / shipboard GPU)

The edge server uses a **local Ollama daemon** plus **faster-whisper** — no cloud AI dependency.

### Required Ollama models
```bash
ollama pull gemma3n:e4b      # near-miss structuring + Master morning brief
ollama pull gemma3n:e2b      # wellbeing check-in chat
ollama pull gemma3:4b        # vision: photo-only hazard drafts
ollama pull embeddinggemma   # duplicate-ticket detection
```
Verify with `ollama list`.

### AI environment variables (`.env`)
| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Local Ollama daemon |
| `OLLAMA_STRUCTURE_MODEL` | `gemma3n:e4b` | Report structuring + brief |
| `OLLAMA_CHAT_MODEL` | `gemma3n:e2b` | Check-in chat turns |
| `OLLAMA_VISION_MODEL` | `gemma3:4b` | Photo-only draft description |
| `OLLAMA_EMBED_MODEL` | `embeddinggemma` | Duplicate detection embeddings |
| `OLLAMA_TIMEOUT_SECONDS` | `60` | Per-call timeout |
| `WHISPER_MODEL_SIZE` | `medium` | faster-whisper model |
| `WHISPER_DEVICE` | `cuda` | Falls back to `small`/CPU/int8 automatically |
| `WHISPER_COMPUTE_TYPE` | `float16` | CUDA compute type |

### GPU / Whisper setup (Tesla T4 / CUDA 12)

faster-whisper 1.2.x needs **PyAV &lt; 15** (`av.open(..., metadata_errors=...)` was removed in PyAV 15+). CTranslate2 on GPU also needs CUDA 12 cuBLAS/cuDNN wheels on `LD_LIBRARY_PATH`.

```bash
cd server/edge
source .venv/bin/activate   # or your edge venv

# 1) Pin PyAV (binary wheel) — required for decode
pip install --only-binary=:all: "av>=12,<15"

# 2) CUDA 12 libs used by CTranslate2 (optional extra)
pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"
# equivalent: pip install -e ".[gpu]"

# 3) Confirm GPU visible
nvidia-smi

# 4) One-line CUDA Whisper smoke test (~few seconds after model download)
python -c "from faster_whisper import WhisperModel; m=WhisperModel('medium', device='cuda', compute_type='float16'); print('ok', m)"
```

**systemd:** `run_edge.sh` prepends
`<venv>/lib/python3.12/site-packages/nvidia/{cublas,cudnn}/lib` to `LD_LIBRARY_PATH` when those dirs exist (CPU-only hosts are unchanged). Optional drop-in if the unit does not call `run_edge.sh`:

```bash
sudo systemctl edit beacon-edge
```

```ini
[Service]
# Resolve purelib once: python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])'
Environment="LD_LIBRARY_PATH=/path/to/venv/lib/python3.12/site-packages/nvidia/cublas/lib:/path/to/venv/lib/python3.12/site-packages/nvidia/cudnn/lib"
```

Then `sudo systemctl restart beacon-edge`.

ASR empty / failed paths **never** return HTTP 422 `transcription_failed`; they continue structuring with `FALLBACK_TRANSCRIPT` and set `asr_fallback_used: true` on the structure response.

### Ops: did someone test voice / reports?

Edge emits structured INFO/WARNING lines (no transcript body). On the VM:

```bash
sudo journalctl -u beacon-edge --since "1 hour ago" | \
  grep -E "draft created|ASR ok|ASR failed|structure ok|ticket submitted|checkin voice"
```

| Log fragment | Meaning |
|---|---|
| `draft created … has_audio=true` | Voice (or audio) attached to a draft |
| `ASR ok … transcript_len=N` | Whisper produced real text |
| `ASR failed … reason=…` | Fallback transcript used |
| `structure ok … asr_fallback_used=false` | Structured from real ASR |
| `ticket submitted …` | Report fully submitted |

Crew/Dashboard web apps also send GA4 page views + report funnel events when online (`VITE_GA_MEASUREMENT_ID`).

### Smoke checks
```bash
# 1. Ollama reachable
curl -s http://127.0.0.1:11434/api/tags | head -c 200

# 2. Report structuring (text draft -> structured fields, not just keyword fallback)
#    POST /reports/drafts (text=...) then POST /reports/drafts/{id}/structure

# 3. Photo-only draft -> vision description (gemma3:4b)
# 4. Check-in chat: POST /checkins (mode=chat) then POST /checkins/{id}/turn -> non-scripted reply
# 5. Voice: POST /checkins/{id}/voice with audio -> real Whisper transcript
# 6. Master brief: POST /master/brief/regenerate -> response contains "generated_by_model": "ollama"
```
With Ollama stopped, all endpoints must still answer using offline heuristics/fallbacks.
