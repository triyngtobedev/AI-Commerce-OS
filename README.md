# AI-Commerce-OS

> Pipeline automatizado para **canais dark no YouTube** — transforma um tema em vídeo documentário 16:9 (~8 min) com narração, visuais, legendas karaoke e assets prontos para publicação.

## O que o projeto faz

O AI-Commerce-OS executa um pipeline **YouTube Dark** de ponta a ponta:

1. **Tema → roteiro** — IA escreve narrativa documental (Gemini → Groq → OpenRouter como fallback)
2. **Roteiro → cenas** — divide em cenas cronometradas com queries visuais e ritmo emocional
3. **Cenas → mídia** — arquivos de stock (Wikimedia, Pixabay, Pexels) ou imagens geradas por IA (**Flux Schnell**) animadas com **Ken Burns / parallax**
4. **Narração** — **Edge TTS** (voz neural PT-BR gratuita), com fallback Azure SSML
5. **Legendas** — alinhamento por palavra com **Whisper** → legendas **ASS estilo karaoke** (blocos sincronizados + destaque de palavras-chave)
6. **Render** — composição com **FFmpeg**, color grade e sincronização da timeline
7. **Export** — `video_final.mp4`, SRT/ASS, thumbnail, capítulos e metadados

Clips **T2V** (máximo **2 cenas por vídeo**) são delegados ao **n8n → Replicate Wan 2.6** quando stock/foto animada não bastam.

Existe também um pipeline legado **TikTok Shop** (9:16, vídeos de afiliados), mas o foco ativo é o fluxo de canal dark no YouTube.

---

## Stack atual

| Camada | Tecnologia | Função |
|--------|------------|--------|
| **API na nuvem** | [FastAPI](https://fastapi.tiangolo.com/) no [Railway](https://railway.app) | Endpoints HTTP para disparo, status de jobs, callbacks de cenas |
| **Automação local** | [n8n](https://n8n.io/) (Docker) | Agendamento diário + orquestração assíncrona de T2V |
| **Imagens IA** | Replicate / HF Router → **Flux Schnell** | Still frames quando stock falha |
| **Vídeo IA** | Replicate → **Wan 2.6** T2V | Até 2 clips cinematográficos por vídeo (720p, 5s) |
| **Narração** | **Edge TTS** (+ fallback Azure SSML) | Voiceover neural PT-BR |
| **Sincronia de legendas** | **faster-whisper** | Timestamps reais por palavra a partir do áudio final |
| **Legendas** | **ASS** (+ export SRT) | Blocos karaoke com destaque de palavras-chave |
| **Motion** | **Ken Burns / parallax** (FFmpeg) | Anima stills — sem slideshow estático |
| **Render** | **FFmpeg** | Clips, concat, color grade, mux final |
| **Roteiro IA** | Gemini, Groq, OpenRouter | Análise, roteiros e metadados |

---

## Arquitetura com n8n

O n8n fica nas **bordas** do sistema — dispara o pipeline e orquestra geração T2V cara. O pipeline Python (`main.py`) continua funcionando standalone via CLI.

```
┌─────────────┐     POST /api/v1/pipeline/run      ┌──────────────────┐
│  n8n        │ ─────────────────────────────────► │  FastAPI :8000   │
│  (Docker)   │                                    │  (Railway/local) │
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

| Passo | Componente | Ação |
|-------|------------|------|
| 1 | n8n Schedule | `POST /api/v1/pipeline/run` com topic/platform |
| 2 | FastAPI | Cria job, dispara subprocess `main.py` |
| 3 | Pipeline | Cenas T2V: `request_scene_generation()` |
| 4 | n8n Webhook | Orquestra Replicate Wan 2.6 → fallback HF Router |
| 5 | n8n Callback | `POST /api/v1/scenes/callback` com `video_path` |
| 6 | scene_waiter | Poll no job store até cena pronta |
| 7 | Pipeline | Continua render FFmpeg (Ken Burns nas cenas de foto) |

Ative delegação de cenas com `USE_N8N_FOR_SCENES=true` no `.env`.

Referência técnica: [`docs/n8n_integration.md`](docs/n8n_integration.md)

---

## Como rodar localmente

### Pré-requisitos

- **Python 3.10+**
- **FFmpeg** no `PATH`
- **Docker** (para n8n)
- Chaves de API (veja abaixo)

### 1. Clone e instale

```bash
git clone https://github.com/triyngtobedev/AI-Commerce-OS.git
cd AI-Commerce-OS

python -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows

pip install -r requirements.txt
cp .env.example .env
```

### 2. Configure o `.env`

Mínimo para produção YouTube Dark:

```env
# IA (pelo menos uma obrigatória)
GEMINI_API_KEY=
GROQ_API_KEY=

# Imagens — Flux Schnell via HF Router
HF_API_TOKEN=

# T2V — Replicate Wan 2.6 (usado pelo n8n, máx. 2 cenas/vídeo)
REPLICATE_API_TOKEN=

# Narração — Edge TTS funciona sem chave; Azure opcional
# AZURE_SPEECH_KEY=
# AZURE_SPEECH_REGION=

# Whisper (tamanho do modelo)
WHISPER_MODEL_SIZE=small

# Integração n8n
USE_N8N_FOR_SCENES=false
PIPELINE_API_KEY=sua_chave_secreta
PIPELINE_API_BASE_URL=http://127.0.0.1:8000
N8N_CALLBACK_BASE_URL=http://host.docker.internal:8000
N8N_SCENE_WEBHOOK_URL=http://localhost:5678/webhook/scene-generation
N8N_WEBHOOK_SECRET=

# YouTube OAuth (upload automático)
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
YOUTUBE_REFRESH_TOKEN=
```

Gere um segredo aleatório:

```bash
openssl rand -hex 32
```

### 3. Suba o n8n (Docker)

```bash
cd infra
cp .env.n8n.example .env.n8n
docker compose -f docker-compose.local.yml up -d
```

Abra **http://localhost:5678** e importe os workflows de `infra/n8n_workflows/`.

### 4. Inicie a FastAPI (uvicorn)

```bash
# na raiz do projeto
chmod +x api/run_api.sh
./api/run_api.sh
```

Health check: `curl http://127.0.0.1:8000/api/v1/health`

### 5. Execute o pipeline

**CLI (sem n8n):**

```bash
python main.py --platform youtube_dark
python main.py --platform youtube_dark --research   # descobrir temas automaticamente
python main.py --platform youtube_dark --upload       # publicar no YouTube
```

**Via API local (n8n ou manual):**

```bash
curl -X POST http://127.0.0.1:8000/api/v1/pipeline/run \
  -H "X-API-Key: SUA_PIPELINE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"platform": "youtube_dark", "topic": "A verdade sobre a Biblioteca de Alexandria"}'
```

Cada execução grava artefatos em `output/youtube_dark/<slug>/`: `video_final.mp4`, `captions.ass`, `legendas.srt` e JSONs de metadados.

---

## Como disparar na nuvem via API

O processamento pesado (FFmpeg, Whisper, render) roda no **Railway**. Seu PC só envia o pedido e baixa o MP4.

### Configuração (uma vez)

1. Deploy no Railway — guia: [`docs/deploy-railway.md`](docs/deploy-railway.md)
2. URL de produção: `https://ai-commerce-os-production-b4f9.up.railway.app`
3. No `.env` local:

```env
CLOUD_API_URL=https://ai-commerce-os-production-b4f9.up.railway.app
CLOUD_API_KEY=<mesmo valor de PIPELINE_API_KEY no Railway>
```

### Disparar via cliente Python

```bash
python scripts/cloud/gerar_video.py --topic "A verdade sobre a Biblioteca de Alexandria"
python scripts/cloud/gerar_video.py --topic "Seu tema" --production
python scripts/cloud/gerar_video.py --topic "Seu tema" --template lofi_dark
```

### Disparar via curl (API direta)

```bash
curl -X POST https://ai-commerce-os-production-b4f9.up.railway.app/api/v1/pipeline/run \
  -H "X-API-Key: SUA_CLOUD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"platform": "youtube_dark", "topic": "Seu tema aqui"}'
```

Acompanhe o status:

```bash
curl https://ai-commerce-os-production-b4f9.up.railway.app/api/v1/pipeline/status/{job_id} \
  -H "X-API-Key: SUA_CLOUD_API_KEY"
```

Automação diária (8h BRT): `.\infra\ativar-n8n.ps1` dispara o Railway a partir do n8n local.

---

## Custo estimado

Pipeline otimizado para **~$0,03 por vídeo** no caminho padrão (sem T2V):

| Item | Custo | Observação |
|------|-------|------------|
| Stock (Wikimedia/Pixabay/Pexels) | $0,00 | Fonte principal para cenas documentais |
| Flux Schnell (HF Router) | ~$0,00–0,02 | Créditos free tier; fallback quando stock falha |
| Ken Burns (FFmpeg) | $0,00 | Anima stills localmente |
| Edge TTS | $0,00 | Vozes neurais gratuitas |
| Whisper | $0,00 | CPU local (`faster-whisper`) |
| Gemini/Groq (roteiro) | ~$0,01 | Cache reduz custo em repetições |
| **Total típico (imagens + Ken Burns)** | **~$0,03** | Sem clips T2V |

**Teto T2V:** no máximo **2 cenas T2V por vídeo** via n8n → Replicate Wan 2.6 (~$0,25/clip, 5s 720p). Com 2 clips T2V o teto sobe para ~$0,53/vídeo; o caminho padrão só com imagens permanece perto de $0,03.

---

## YouTube OAuth — upload automático

O upload automático para o YouTube está configurado via OAuth. Configure as variáveis `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET` e `YOUTUBE_REFRESH_TOKEN` no `.env`.

**Fluxo interativo (recomendado):**

```bash
python main.py --youtube-auth
```

**Script alternativo com JSON de credenciais:**

```bash
python scripts/youtube/gerar_token.py
```

**Validar conexão:**

```bash
python main.py --youtube-validate
```

**Publicar após gerar o vídeo:**

```bash
python main.py --platform youtube_dark --upload
```

Guia completo: [`docs/youtube_oauth.md`](docs/youtube_oauth.md)

---

## Estrutura do projeto

```
AI-Commerce-OS/
├── main.py                     # Entry point CLI
├── api/                        # FastAPI bridge (n8n + nuvem)
│   ├── main_api.py
│   ├── routers/                # pipeline, scenes, youtube, analytics
│   └── run_api.sh              # launcher uvicorn
├── src/
│   ├── n8n_integration/        # scene_client, scene_waiter, config
│   └── video_generator.py      # Replicate Wan 2.6 / fallbacks Kling
├── scripts/
│   ├── pipeline/youtube_pipeline.py
│   ├── video/                  # scene_renderer, subtitle_engine, whisper_aligner
│   ├── audio/                  # Edge TTS, narration engine
│   ├── youtube/                # engines YouTube
│   └── cloud/                  # gerar_video.py — cliente Railway
├── infra/
│   ├── docker-compose.local.yml  # n8n local (HTTP)
│   └── n8n_workflows/          # trigger + scene orchestrator JSONs
├── prompts/                    # templates de prompts IA
├── docs/                       # guias detalhados
└── output/                     # artefatos gerados (gitignored)
```

---

## Documentação

| Guia | Descrição |
|------|-----------|
| [`docs/n8n_integration.md`](docs/n8n_integration.md) | Setup n8n completo (local + VM produção) |
| [`docs/ATIVAR-N8N.md`](docs/ATIVAR-N8N.md) | Automação diária em um comando |
| [`docs/deploy-railway.md`](docs/deploy-railway.md) | Deploy na nuvem (Railway) |
| [`docs/youtube_oauth.md`](docs/youtube_oauth.md) | OAuth e upload YouTube |
| [`docs/STATUS.md`](docs/STATUS.md) | Snapshot atual do projeto |
| [`docs/aicommerceos-content-guide.md`](docs/aicommerceos-content-guide.md) | Guia de conteúdo para canal dark |

---

## Status

Pipeline YouTube Dark funcional de ponta a ponta:

- Stock + Flux Schnell com motion Ken Burns
- Narração Edge TTS + legendas ASS karaoke sincronizadas por Whisper
- Render FFmpeg (1920×1080, ~8 min)
- FastAPI no Railway + orquestração de cenas n8n (Replicate Wan 2.6)
- YouTube OAuth configurado para upload automático
- Custo padrão ~$0,03/vídeo

Veja [`docs/STATUS.md`](docs/STATUS.md) para o snapshot mais recente.
