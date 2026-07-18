# AI-Commerce-OS

> Plataforma de automação com IA para descoberta de oportunidades, produção de vídeos e publicação em múltiplas plataformas.

## Visão Geral

O **AI-Commerce-OS** transforma dados brutos (produtos ou temas) em pacotes completos de conteúdo prontos para publicação. O sistema analisa oportunidades com IA, gera roteiros e narração, busca mídias, monta cenas, renderiza vídeos e exporta tudo de forma automatizada.

Atualmente suporta duas plataformas:

| Plataforma | Tipo de conteúdo | Formato | Monetização |
|---|---|---|---|
| **TikTok Shop** | Produtos de afiliado | Vertical 9:16 (~30s) | Comissão de afiliado |
| **YouTube Dark** | Temas de história e curiosidades | Horizontal 16:9 (~8 min) | AdSense |

O objetivo é reduzir o trabalho manual na criação de conteúdo digital e permitir testes rápidos de novos produtos ou nichos.

---

## Arquitetura

O projeto é organizado em **engines modulares** orquestradas por pipelines específicos de cada plataforma. Engines compartilhados (mídia, áudio, renderização) são reutilizados entre os dois fluxos.

```
                    ┌─────────────────────────────────────┐
                    │           main.py (CLI)             │
                    └──────────┬──────────────┬─────────────┘
                               │              │
              ┌────────────────┘              └────────────────┐
              ▼                                                ▼
   ┌──────────────────────┐                      ┌──────────────────────┐
   │  Pipeline TikTok Shop │                      │ Pipeline YouTube Dark │
   └──────────┬───────────┘                      └──────────┬───────────┘
              │                                              │
   ┌──────────▼───────────┐                      ┌──────────▼───────────┐
   │ Coleta de Produtos   │                      │ Coleta / Pesquisa    │
   │ Análise + Score      │                      │ de Temas             │
   │ Oportunidade         │                      │ Análise + Score      │
   │ Decisão              │                      │ Oportunidade         │
   │ Estratégia Criativa  │                      │ Decisão              │
   │ Roteiro + Conteúdo   │                      │ Estratégia YouTube   │
   │ Cenas                │                      │ Roteiro + Conteúdo   │
   └──────────┬───────────┘                      │ Cenas + Capítulos    │
              │                                  └──────────┬───────────┘
              │                                              │
              └──────────────────┬───────────────────────────┘
                                 ▼
              ┌──────────────────────────────────────────────┐
              │           Engines Compartilhados             │
              │  Asset Search → Media Pipeline → TTS →       │
              │  Scene Timeline → Legendas → Renderização  │
              └──────────────────┬───────────────────────────┘
                                 ▼
              ┌──────────────────────────────────────────────┐
              │  Exportação → (YouTube) Upload + Analytics   │
              │  Métricas de Produção                        │
              └──────────────────────────────────────────────┘
```

### Engines

| Engine | Módulo | Responsabilidade |
|---|---|---|
| **AI Router** | `scripts/ai/router.py` | Roteamento Gemini → Groq (fallback) |
| **Analyst** | `scripts/ai/analysts/` | Análise de produtos/temas com IA |
| **Scoring** | `scripts/scoring/` | Pontuação e ranking |
| **Opportunity** | `scripts/affiliate/`, `scripts/youtube/topic_opportunity.py` | Avaliação de oportunidade comercial |
| **Decision** | `scripts/decision/decision_engine.py` | Decisão: criar, testar ou descartar |
| **Creative Strategy** | `scripts/creative/` | DNA criativo (TikTok) |
| **YouTube Strategy** | `scripts/youtube/youtube_strategy.py` | Estratégia documental (YouTube) |
| **Script** | `scripts/creative/`, `scripts/youtube/youtube_script.py` | Geração de roteiros |
| **Content** | `scripts/content/`, `scripts/youtube/youtube_content.py` | Textos, títulos, descrições, tags |
| **Scenes** | `scripts/video/`, `scripts/youtube/youtube_scenes.py` | Estruturação de cenas |
| **Asset Search** | `scripts/video/asset_search.py` | Queries de busca de mídia |
| **Media Pipeline** | `scripts/pipeline/shared_media.py` | Busca e download (Pexels) ou persona |
| **TTS** | `scripts/audio/` | Narração Azure SSML → Edge-TTS → gTTS (fallback) |
| **Scene Timeline** | `scripts/video/scene_timeline.py` | Sincronização cenas ↔ áudio |
| **Subtitles** | `scripts/video/subtitle_generator.py` | Legendas SRT sincronizadas |
| **Renderer** | `scripts/video/renderer.py` | Montagem final via FFmpeg |
| **Thumbnail** | `scripts/youtube/thumbnail_generator.py` | Thumbnail YouTube |
| **Chapters** | `scripts/youtube/chapter_builder.py` | Capítulos para descrição YouTube |
| **Exporter** | `scripts/publisher/` | Pacote de exportação por plataforma |
| **YouTube Upload** | `scripts/publisher/youtube_uploader.py` | Publicação OAuth no YouTube |
| **Analytics** | `scripts/youtube/youtube_analytics.py` | Métricas e insights do canal |
| **Metrics** | `scripts/metrics/metrics_tracker.py` | Histórico de produção |
| **Research** | `scripts/research/topic_research_engine.py` | Pesquisa automática de temas |

---

## Fluxo do Pipeline

### TikTok Shop

```
Produto → Coleta → Análise IA → Score → Ranking → Oportunidade
  → Decisão → Estratégia Criativa → Roteiro → Conteúdo → Cenas
  → Asset Queries → Mídia (Stock/Persona) → TTS → Legendas
  → Renderização 9:16 → Exportação → Dashboard
```

### YouTube Dark

```
Tema → Coleta/Pesquisa → Análise IA → Score → Ranking → Oportunidade
  → Decisão → Estratégia → Roteiro → Conteúdo → Cenas → Capítulos
  → Asset Queries → Mídia (Stock) → TTS → Scene Timeline → Legendas
  → Renderização 16:9 → Thumbnail → Exportação YouTube
  → (Opcional) Upload OAuth → Métricas
```

Cada execução gera uma pasta em `output/<plataforma>/<slug>/` contendo JSONs intermediários, assets, legendas, thumbnail (YouTube) e `video_final.mp4`.

---

## Estrutura do Projeto

```
AI-Commerce-OS/
├── main.py                          # Entrada CLI
├── validar_ativos.py                # Verificação de vídeos gerados
├── requirements.txt
├── .env.example
│
├── scripts/
│   ├── ai/                          # Router e providers (Gemini, Groq)
│   ├── affiliate/                   # Engine de oportunidade (TikTok)
│   ├── audio/                       # TTS e preparação de texto
│   ├── content/                     # Geração de conteúdo (TikTok)
│   ├── core/                        # Platform config, pipeline result
│   ├── creative/                    # Estratégia criativa e roteiros
│   ├── dashboard/                   # Geração de dashboard
│   ├── data_sources/
│   │   ├── tiktok/                  # Coleta de produtos
│   │   └── youtube/                 # Coleta de temas
│   ├── decision/                    # Motor de decisão
│   ├── metrics/                     # Rastreamento de produção
│   ├── pipeline/
│   │   ├── product_pipeline.py      # Pipeline TikTok Shop
│   │   ├── youtube_pipeline.py      # Pipeline YouTube Dark
│   │   └── shared_media.py          # Mídia compartilhada
│   ├── publisher/                   # Exportação e upload YouTube
│   ├── research/                    # Pesquisa automática de temas
│   ├── scoring/                     # Pontuação e ranking
│   ├── utils/                       # Cache IA, prompts, slug
│   ├── video/                       # Cenas, render, legendas, mídia
│   └── youtube/                     # Engines específicos YouTube
│
├── database/
│   ├── products.json                # Catálogo de produtos
│   └── topics_source.json           # Fonte de temas YouTube
│
├── prompts/                         # Templates de prompt para IA
├── api/                             # FastAPI bridge (n8n + nuvem)
├── scripts/cloud/                   # Cliente Railway + entrypoint Docker
├── Dockerfile                       # Imagem de produção (Railway)
├── railway.toml                     # Config deploy Railway
├── docs/
│   ├── STATUS.md                    # Snapshot do status atual
│   ├── deploy-railway.md            # Deploy na nuvem (zero SSH)
│   ├── deploy-nuvem.md              # Resumo deploy
│   ├── n8n_integration.md           # Integração n8n
│   └── youtube_oauth.md             # Guia OAuth do YouTube
│
├── output/                          # Artefatos gerados (gitignored)
├── src/
│   ├── video_generator.py           # Geração de vídeo IA (fallback automático)
│   ├── video_upscaler.py            # Upscale pós-geração (Real-ESRGAN / ffmpeg)
│   └── prompt_builder.py            # Templates de prompt e-commerce
└── cache/                           # Cache de respostas IA (gitignored)
```

---

## Instalação

### Pré-requisitos

- **Python 3.10+**
- **FFmpeg** instalado e disponível no `PATH`
- Chaves de API (ver seção de configuração)

### Passos

```bash
# Clonar o repositório
git clone https://github.com/triyngtobedev/AI-Commerce-OS.git
cd AI-Commerce-OS

# Criar ambiente virtual (recomendado)
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
copy .env.example .env       # Windows
# cp .env.example .env       # Linux/macOS
```

Edite o `.env` com suas chaves de API (detalhes abaixo).

---

## Deploy na Nuvem (Railway)

Gere vídeos **sem travar o PC** — o processamento pesado (FFmpeg, Whisper, render) roda no Railway; você só envia o tema e baixa o MP4.

```powershell
# 1) Deploy: conecte o repo no railway.app (guia completo abaixo)
# 2) Configure no .env local:
#    CLOUD_API_URL=https://seu-app.up.railway.app
#    CLOUD_API_KEY=<mesma PIPELINE_API_KEY do Railway>

# Atalho interativo
.\scripts\cloud\configurar_pc.ps1

# Testar conexão
python scripts/cloud/gerar_video.py --topic "teste de conexão"

# Gerar vídeo completo
.\scripts\cloud\gerar_video.ps1 -Topic "A verdade sobre a Biblioteca de Alexandria"
```

### Automação diária (n8n — sem comandos manuais)

Depois do Railway ativo, rode **uma vez**:

```powershell
.\infra\ativar-n8n.ps1
```

O n8n dispara **1 vídeo por dia às 8h** automaticamente. Guia: [`docs/ATIVAR-N8N.md`](docs/ATIVAR-N8N.md)

| Recurso | Detalhe |
|---|---|
| Custo estimado | ~R$ 25/mês (Railway Hobby + 4 GB RAM) |
| Tempo típico | 45–120 min por vídeo |
| Documentação | [`docs/deploy-railway.md`](docs/deploy-railway.md) |
| Status do projeto | [`docs/STATUS.md`](docs/STATUS.md) |

---

## Configuração do Ambiente

Copie `.env.example` para `.env` e preencha:

```env
# APIs de IA (pelo menos uma obrigatória)
GEMINI_API_KEY=sua_chave_gemini
GROQ_API_KEY=sua_chave_groq

# Mídia stock (Pexels)
PEXELS_API_KEY=sua_chave_pexels

# Pixabay (fallback de mídia stock, gratuito)
PIXABAY_API_KEY=

# Modo de mídia: stock (padrão) | persona
# persona = gera imagens IA únicas por cena via Pollinations.ai (gratuito, sem chave)
CONTENT_MODE=stock

# Plataforma padrão: tiktok_shop | youtube_dark
DEFAULT_PLATFORM=tiktok_shop

# YouTube OAuth (upload + analytics)
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
YOUTUBE_REFRESH_TOKEN=

# Controle de publicação YouTube
YOUTUBE_AUTO_UPLOAD=false
YOUTUBE_DRY_RUN=false
YOUTUBE_PUBLISH_ENABLED=true

# Azure Speech (TTS com SSML — motor principal de narração)
AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=

# Pipeline na nuvem (Railway — opcional, para gerar_video.py)
CLOUD_API_URL=
CLOUD_API_KEY=
PIPELINE_API_KEY=              # mesma chave no Railway e no PC
```

| Variável | Descrição |
|---|---|
| `GEMINI_API_KEY` | API Google Gemini (provider principal) |
| `GROQ_API_KEY` | API Groq (fallback automático) |
| `PEXELS_API_KEY` | Busca de vídeos/imagens stock (Pexels) |
| `PIXABAY_API_KEY` | Fallback de mídia stock gratuito (YouTube Dark) |
| `CONTENT_MODE` | `stock` usa Pexels/Pixabay; `persona` gera imagens IA por cena via Pollinations.ai (gratuito) + Ken Burns |
| `YOUTUBE_AUTO_UPLOAD` | Publica automaticamente após produção |
| `YOUTUBE_DRY_RUN` | Simula upload sem publicar |
| `YOUTUBE_PUBLISH_ENABLED` | Habilita/desabilita publicação globalmente |
| `AZURE_SPEECH_KEY` | Chave Azure Cognitive Services Speech (TTS com SSML) |
| `AZURE_SPEECH_REGION` | Região Azure (ex.: `eastus`, `brazilsouth`) |

### Geração de vídeo IA (VideoGenerator)

Ordem de fallback automático: **Kling Web (grátis)** → **fal.ai Kling 2.6 Pro** → **Replicate Wan 2.6** → **fal.ai Wan (HF Router)**.

```env
# Mínimo para primeiro vídeo real (menor fricção):
HF_API_TOKEN=hf_...          # huggingface.co/settings/tokens
                             # Permissão: "Make calls to Inference Providers"
                             # Crédito free: US$ 0,10/mês

# Fallbacks opcionais:
REPLICATE_API_TOKEN=r8_...   # replicate.com — Wan 2.6 (~$0,25/clip 5s 720p)
FAL_KEY=fal_...            # fal.ai — Kling 2.6 Pro premium (~$0,35/clip)
KLING_EMAIL=seu@email.com    # Kling web — 66 créditos/dia (tier grátis, tentado primeiro)
KLING_PASSWORD=suasenha

VIDEO_OUTPUT_DIR=./output/videos
VIDEO_TIMEOUT=300
```

**Teste rápido** (gera `./output/videos/test_real.mp4`):

```bash
python -m src.video_generator \
  --prompt "sneaker product shot, studio lighting, slow zoom" \
  --output ./output/videos/test_real.mp4
```

**Upscale pós-geração** (480p → 960p): o pipeline aplica automaticamente após geração IA. Requer **ffmpeg** no PATH; **realesrgan-ncnn-vulkan** é opcional (melhor qualidade).

Instalação do Real-ESRGAN (opcional):

```bash
# Windows — baixe o release em:
# https://github.com/xinntao/Real-ESRGAN/releases
# Extraia e adicione realesrgan-ncnn-vulkan.exe ao PATH

# Linux (exemplo)
wget https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip
unzip realesrgan-ncnn-vulkan-*.zip
export PATH="$PATH:/caminho/para/realesrgan-ncnn-vulkan"
```

Sem Real-ESRGAN, o upscale usa filtro Lanczos do ffmpeg (qualidade inferior, mas funcional).

**Kling Web (Playwright — fallback gratuito):**

```bash
pip install playwright
python -m playwright install chromium
```

Fluxo automatizado: `kling.ai/app/video/new` → One-click Sign In → **Sign in with email** → Generate.

Sessão salva em `cache/kling_storage_state.json` após login bem-sucedido (reutilizada nas próximas execuções).

Debug visual (salva screenshots em `debug/`):

```bash
# Windows PowerShell
$env:KLING_DEBUG="1"
$env:PLAYWRIGHT_BROWSERS_PATH="$env:USERPROFILE\AppData\Local\ms-playwright"
python -m src.video_generator --prompt "test" --output ./output/videos/test_real.mp4

# Browser visível (validação manual)
$env:KLING_HEADFUL="1"
```

Validação de tokens e webhook n8n:

```bash
python scripts/validate_tokens.py
python scripts/test_n8n_scene_webhook.py
```

---

## Autenticação com o YouTube

Necessária para upload automático e analytics. Guia completo em [`docs/youtube_oauth.md`](docs/youtube_oauth.md).

### Configuração rápida

```bash
# Fluxo OAuth interativo (recomendado)
python main.py --youtube-auth

# Validar credenciais
python main.py --youtube-validate

# Consultar métricas do canal
python main.py --youtube-analytics
```

Pré-requisitos no Google Cloud: ativar **YouTube Data API v3** e **YouTube Analytics API**, criar credenciais OAuth do tipo "Aplicativo para computador".

---

## Como Executar

### TikTok Shop (padrão)

```bash
# Pipeline completo para produtos
python main.py

# Equivalente explícito
python main.py --platform tiktok_shop
```

### YouTube Dark

```bash
# Produzir 1 vídeo a partir dos temas em database/topics_source.json
python main.py --platform youtube_dark

# Pesquisar novos temas via IA antes de produzir
python main.py --platform youtube_dark --research

# Produzir e publicar no YouTube (privado)
python main.py --platform youtube_dark --upload

# Produzir múltiplos vídeos com privacidade pública
python main.py --platform youtube_dark --max-videos 3 --upload --privacy public
```

#### Reprocessamento (`--rerun` / `--force`)

`--rerun` é alias de `--force` — ambos definem a mesma variável interna (`force=True`).

| Modo | Comando | Comportamento |
|---|---|---|
| Normal | `python main.py --platform youtube_dark` | Seleciona apenas temas **não processados**; protege contra duplicação |
| Desenvolvimento | `python main.py --platform youtube_dark --rerun` | Reprocessa tema já gerado; reutiliza a pasta existente e atualiza artefatos |

Em `--production`, o pipeline resumível também invalida o `stage_cache` para garantir reexecução completa.

### Ambas as plataformas

```bash
python main.py --platform all
```

### Utilitários

```bash
# Verificar status dos vídeos gerados
python validar_ativos.py

# Executar testes unitários (módulos YouTube)
python -m unittest scripts.youtube.test_youtube_pipeline_e2e -v
```

### Flags disponíveis

| Flag | Descrição |
|---|---|
| `--platform` | `tiktok_shop`, `youtube_dark` ou `all` |
| `--research` | Pesquisa automática de temas (YouTube) |
| `--upload` | Publica no YouTube após produção |
| `--privacy` | `private`, `unlisted` ou `public` (sobrescreve `UPLOAD_VISIBILITY`) |
| `UPLOAD_VISIBILITY` | Variável `.env`: `private` \| `unlisted` \| `public` — controla visibilidade em produção |
| `--max-videos` | Limite de vídeos por execução |
| `--force` / `--rerun` | Reprocessar temas já gerados (aliases — ver seção Reprocessamento) |
| `--youtube-auth` | Configura OAuth interativamente |
| `--youtube-validate` | Valida credenciais OAuth |
| `--youtube-analytics` | Exibe métricas do canal |
| `--youtube-branding` | Gera assets de identidade visual do canal |
| `--apply` | Aplica branding no canal via API (com `--youtube-branding`) |

---

## Principais Funcionalidades

### Pesquisa e Análise
- Coleta de produtos (TikTok) e temas (YouTube)
- Pesquisa automática de temas via IA (`--research`)
- Análise de potencial com scoring e ranking
- Motor de decisão baseado em score de oportunidade

### Inteligência Artificial
- Roteamento Gemini com fallback Groq
- Prompts especializados por plataforma em `prompts/`
- Cache de respostas IA em `cache/` (reduz custos)

### Produção de Vídeo
- Geração de cenas, queries de mídia e download automático (Pexels)
- **VideoGenerator** com fallback Kling Web → fal Kling 2.6 → Replicate Wan 2.6 → HF Wan2.2
- Upscale automático 480p → 960p (`src/video_upscaler.py`)
- Narração Azure Speech SDK (SSML por seção) com fallback Edge-TTS e gTTS
- Sincronização cena-a-cena via scene timeline
- Legendas SRT e renderização FFmpeg
- Thumbnail e capítulos (YouTube)

### Publicação e Métricas
- Exportação de pacote completo por plataforma
- Upload OAuth no YouTube com controle de privacidade
- YouTube Analytics com recomendações de otimização
- Rastreamento de produção em `database/metrics.json`

---

## Tecnologias

| Tecnologia | Uso |
|---|---|
| **Python 3.10+** | Linguagem principal |
| **Google Gemini** | Provider principal de IA |
| **Groq (Llama 3.3)** | Fallback de IA |
| **Azure Speech SDK** | Narração neural com SSML (motor principal) |
| **Edge-TTS** | Narração automática (fallback gratuito) |
| **FFmpeg** | Renderização de vídeo |
| **Pexels API** | Mídia stock |
| **Pillow** | Geração de thumbnails |
| **Google APIs** | YouTube Data, Analytics e OAuth |
| **python-dotenv** | Gerenciamento de variáveis de ambiente |

---

## Status Atual

> Snapshot detalhado: [`docs/STATUS.md`](docs/STATUS.md) (atualizado em jul/2026)

Versão funcional com suporte multi-plataforma, API HTTP e deploy na nuvem.

**Local (CLI)**
- Análise de produtos e temas com IA
- Geração de roteiros, conteúdo e cenas
- Produção automática de vídeos (vertical 9:16 e horizontal 16:9)
- VideoGenerator com fallback Kling Web → fal → Replicate → HF
- Narração TTS (Azure → Edge-TTS → gTTS) e legendas sincronizadas
- Pipeline YouTube Dark end-to-end + upload OAuth + analytics
- Reprocessamento com `--rerun` / `--force`

**Nuvem e automação**
- API FastAPI (`/api/v1/pipeline/run`, status, download)
- Deploy Docker no Railway (`Dockerfile`, `railway.toml`)
- Cliente local `scripts/cloud/gerar_video.py` (tema → MP4 na pasta `downloads/`)
- Integração n8n pronta para ativação (`infra/ativar-n8n.ps1` + [`docs/ATIVAR-N8N.md`](docs/ATIVAR-N8N.md))

**Qualidade**
- Testes unitários YouTube, VideoGenerator e APIs de vídeo
- Validação de tokens: `python scripts/validate_tokens.py`

---

## Roadmap

### Concluído
- [x] Pipeline TikTok Shop funcional
- [x] Pipeline YouTube Dark end-to-end
- [x] Suporte multi-plataforma com engines compartilhados
- [x] Upload automático YouTube (OAuth)
- [x] YouTube Analytics
- [x] Scene timeline e sincronização cena-áudio
- [x] Pesquisa automática de temas
- [x] Métricas de produção
- [x] VideoGenerator multi-provider (Kling, fal, Replicate, HF)
- [x] Containerização Docker + deploy Railway
- [x] API HTTP para acionamento remoto do pipeline

### Em progresso
- [x] Integração n8n (workflows + bridge HTTP + guia de ativação)
- [ ] Validação end-to-end na nuvem (Railway + `gerar_video.py`)

### Próximos passos
- [ ] Dashboard web para monitoramento
- [ ] Otimização baseada em analytics (feedback loop)
- [ ] Suporte a novos nichos e plataformas
- [ ] Modo persona reativado para TikTok
- [ ] Testes automatizados em CI/CD

---

## Autor

Projeto desenvolvido como estudo e construção de uma plataforma de automação com IA aplicada ao comércio digital e criação de conteúdo.
