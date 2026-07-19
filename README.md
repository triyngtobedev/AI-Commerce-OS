# AI-Commerce-OS

> Automated pipeline for **dark YouTube channels** — turns a topic into a finished 16:9 documentary-style video (~8 min) with narration, visuals, karaoke subtitles, and export-ready assets.

## What It Does

AI-Commerce-OS runs an end-to-end **YouTube Dark** production pipeline:

1. **Topic → script** — AI writes a documentary narrative (Gemini → Groq → OpenRouter fallback)
2. **Script → scenes** — breaks into timed scenes with visual queries and emotional pacing
3. **Scenes → media** — stock archives (Wikimedia, Pixabay, Pexels) or AI-generated stills (**Flux Schnell**) animated with **Ken Burns / parallax**
4. **Narration** — **Edge TTS** (free neural PT-BR) with Azure SSML fallback
5. **Subtitles** — **Whisper** word alignment → **ASS karaoke-style** captions (word-timed blocks + keyword highlights)
6. **Render** — **FFmpeg** compositing, color grade, scene timeline sync
7. **Export** — `video_final.mp4`, SRT/ASS, thumbnail, chapters, metadata

Optional **T2V clips** (max **2 scenes per video**) are delegated to **n8n → Replicate Wan 2.6** when stock/photo animation is not enough.

A legacy **TikTok Shop** pipeline (9:16 affiliate videos) still exists but the active focus is the dark YouTube channel workflow.

---

## Tech Stack

| Layer | Technology | Role |
|-------|------------|------|
| **API bridge** | [FastAPI](https://fastapi.tiangolo.com/) + uvicorn | HTTP endpoints for n8n triggers, job status, scene callbacks |
| **Automation** | [n8n](https://n8n.io/) (Docker) | Scheduled pipeline runs + async T2V orchestration |
| **Image AI** | Replicate / HF Router → **Flux Schnell** | Scene stills when stock fails |
| **Video AI** | Replicate → **Wan 2.6** T2V | Up to 2 cinematic clips per video (720p, 5s) |
| **Narration** | **Edge TTS** (+ Azure SSML fallback) | Neural PT-BR voiceover |
| **Subtitle sync** | **faster-whisper** | Real word timestamps from final audio |
| **Subtitles** | **ASS** (+ SRT export) | Karaoke-style blocks with keyword color highlights |
| **Motion** | **Ken Burns / parallax** (FFmpeg) | Animates still images — no static slideshows |
| **Render** | **FFmpeg** | Scene clips, concat, color grade, final mux |
| **Script AI** | Gemini, Groq, OpenRouter | Analysis, scripts, content metadata |

---

## n8n Integration Architecture

n8n sits at the **edges** of the system — it triggers the pipeline and orchestrates expensive T2V generation. The Python pipeline (`main.py`) keeps working standalone via CLI.

```
┌─────────────┐     POST /api/v1/pipeline/run      ┌──────────────────┐
│  n8n        │ ─────────────────────────────────► │  FastAPI :8000   │
│  (Docker)   │                                    │  (uvicorn)       │
│  Schedule   │ ◄── GET /pipeline/status/{id} ──── │                  │
└──────┬──────┘                                    └────────┬─────────┘
       │                                                      │
       │  POST /webhook/scene-generation                      │ subprocess
       │ ◄─────────────────────────────────────────────────── │ main.py
       │                                                      │
       ▼                                                      ▼
┌─────────────┐     POST /api/v1/scenes/callback   ┌──────────────────┐
│  n8n        │ ─────────────────────────────────► │  scene_waiter    │
│  Workflow   │   (video_path, provider, status)   │  (poll + Event)  │
│  02         │                                    └──────────────────┘
└──────┬──────┘
       │
       ▼
  Replicate Wan 2.6 T2V
  (fallback: HF Router → fal.ai Wan2.2)
```

### Flow (step by step)

| Step | Component | Action |
|------|-----------|--------|
| 1 | n8n Schedule | `POST /api/v1/pipeline/run` with topic/platform |
| 2 | FastAPI | Creates job, spawns `main.py` subprocess |
| 3 | Pipeline | For scenes needing T2V: `request_scene_generation()` |
| 4 | n8n Webhook | Orchestrates Replicate Wan 2.6 → HF Router fallback |
| 5 | n8n Callback | `POST /api/v1/scenes/callback` with `video_path` |
| 6 | scene_waiter | Polls job store until scene is ready |
| 7 | Pipeline | Continues FFmpeg render (Ken Burns for photo scenes) |

Enable n8n scene delegation with `USE_N8N_FOR_SCENES=true` in `.env`.

Technical reference: [`docs/n8n_integration.md`](docs/n8n_integration.md)

---

## Local Setup

### Prerequisites

- **Python 3.10+**
- **FFmpeg** on `PATH`
- **Docker** (for n8n)
- API keys (see below)

### 1. Clone and install

```bash
git clone https://github.com/triyngtobedev/AI-Commerce-OS.git
cd AI-Commerce-OS

python -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows

pip install -r requirements.txt
cp .env.example .env
```

### 2. Configure `.env`

Minimum for YouTube Dark production:

```env
# AI (at least one required)
GEMINI_API_KEY=
GROQ_API_KEY=

# Image fallback — Flux Schnell via HF Router (free tier ~$0.10/mo)
HF_API_TOKEN=

# T2V — Replicate Wan 2.6 (used by n8n, max 2 scenes/video)
REPLICATE_API_TOKEN=

# Narration — Edge TTS works with no key; Azure optional
# AZURE_SPEECH_KEY=
# AZURE_SPEECH_REGION=

# Whisper subtitle alignment (optional model size)
WHISPER_MODEL_SIZE=small

# n8n integration
USE_N8N_FOR_SCENES=false
PIPELINE_API_KEY=your_secret_key
PIPELINE_API_BASE_URL=http://127.0.0.1:8000
N8N_CALLBACK_BASE_URL=http://host.docker.internal:8000
N8N_SCENE_WEBHOOK_URL=http://localhost:5678/webhook/scene-generation
N8N_WEBHOOK_SECRET=
```

Generate a random secret:

```bash
openssl rand -hex 32
```

### 3. Start n8n (Docker)

```bash
cd infra
cp .env.n8n.example .env.n8n
docker compose -f docker-compose.local.yml up -d
```

Open **http://localhost:5678** and import workflows from `infra/n8n_workflows/`.

### 4. Start FastAPI (uvicorn)

```bash
# from project root
chmod +x api/run_api.sh
./api/run_api.sh
```

Health check: `curl http://127.0.0.1:8000/api/v1/health`

### 5. Run the pipeline

**CLI (no n8n):**

```bash
python main.py --platform youtube_dark
python main.py --platform youtube_dark --research   # auto-discover topics
python main.py --platform youtube_dark --upload       # publish to YouTube
```

**Via API (n8n or manual):**

```bash
curl -X POST http://127.0.0.1:8000/api/v1/pipeline/run \
  -H "X-API-Key: YOUR_PIPELINE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"platform": "youtube_dark", "topic": "A verdade sobre a Biblioteca de Alexandria"}'
```

Each run writes artifacts to `output/youtube_dark/<slug>/` including `video_final.mp4`, `captions.ass`, `legendas.srt`, and metadata JSONs.

---

## Cost Breakdown

The pipeline is optimized for **~$0.03 per video** on the default path:

| Item | Cost | Notes |
|------|------|-------|
| Stock media (Wikimedia/Pixabay/Pexels) | $0.00 | Primary source for documentary scenes |
| Flux Schnell images (HF Router) | ~$0.00–0.02 | Free tier credits; fallback when stock fails |
| Ken Burns animation | $0.00 | FFmpeg — animates stills locally |
| Edge TTS narration | $0.00 | Free neural voices |
| Whisper alignment | $0.00 | Local CPU (`faster-whisper`) |
| Gemini/Groq script AI | ~$0.01 | Cached responses reduce repeat cost |
| **Typical total (images + Ken Burns)** | **~$0.03** | No T2V clips used |

**T2V budget cap:** at most **2 T2V scenes per video**, routed through n8n → Replicate Wan 2.6 (~$0.25/clip, 5s 720p). Remaining scenes use stock photos + Ken Burns. With 2 T2V clips the upper bound is ~$0.53/video; the default image-only path stays near $0.03.

---

## Project Structure

```
AI-Commerce-OS/
├── main.py                     # CLI entry point
├── api/                        # FastAPI bridge (n8n + cloud)
│   ├── main_api.py
│   ├── routers/                # pipeline, scenes, youtube, analytics
│   └── run_api.sh              # uvicorn launcher
├── src/
│   ├── n8n_integration/        # scene_client, scene_waiter, config
│   └── video_generator.py      # Replicate Wan 2.6 / Kling fallbacks
├── scripts/
│   ├── pipeline/youtube_pipeline.py
│   ├── video/                  # scene_renderer, subtitle_engine, whisper_aligner
│   ├── audio/                  # Edge TTS, narration engine
│   └── youtube/                # YouTube-specific engines
├── infra/
│   ├── docker-compose.local.yml  # n8n local (HTTP)
│   └── n8n_workflows/          # trigger + scene orchestrator JSONs
├── prompts/                    # AI prompt templates
├── docs/                       # Detailed guides
└── output/                     # Generated artifacts (gitignored)
```

---

## Documentation

| Guide | Description |
|-------|-------------|
| [`docs/n8n_integration.md`](docs/n8n_integration.md) | Full n8n setup (local + production VM) |
| [`docs/ATIVAR-N8N.md`](docs/ATIVAR-N8N.md) | One-command daily automation |
| [`docs/deploy-railway.md`](docs/deploy-railway.md) | Cloud deploy (Railway) |
| [`docs/youtube_oauth.md`](docs/youtube_oauth.md) | YouTube upload OAuth |
| [`docs/STATUS.md`](docs/STATUS.md) | Current project snapshot |
| [`docs/aicommerceos-content-guide.md`](docs/aicommerceos-content-guide.md) | Dark channel content guide |

---

## Cloud Deploy (Optional)

Run heavy processing (FFmpeg, Whisper, render) on [Railway](https://railway.app) instead of your local machine:

```bash
# After Railway deploy (see docs/deploy-railway.md):
python scripts/cloud/gerar_video.py --topic "Seu tema aqui"
```

Set `CLOUD_API_URL` and `CLOUD_API_KEY` in `.env` to match your Railway deployment.

Daily automation: `.\infra\ativar-n8n.ps1` (Windows) triggers Railway from local n8n at 8h BRT.

---

## Status

Functional end-to-end YouTube Dark pipeline with:

- Stock + Flux Schnell images with Ken Burns motion
- Edge TTS narration + Whisper-synced ASS karaoke subtitles
- FFmpeg render (1920×1080, ~8 min)
- FastAPI HTTP bridge + n8n scene orchestration (Replicate Wan 2.6)
- Optional Railway cloud deploy and YouTube OAuth upload

See [`docs/STATUS.md`](docs/STATUS.md) for the latest snapshot.
