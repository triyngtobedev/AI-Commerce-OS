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
├── docs/
│   └── youtube_oauth.md             # Guia OAuth do YouTube
│
├── output/                          # Artefatos gerados (gitignored)
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

Versão funcional com suporte multi-plataforma.

- Análise de produtos e temas com IA
- Geração de roteiros, conteúdo e cenas
- Produção automática de vídeos (vertical e horizontal)
- Narração TTS e legendas sincronizadas
- Pipeline YouTube Dark end-to-end
- Upload automático no YouTube via OAuth
- YouTube Analytics e métricas de produção
- Testes unitários e E2E para módulos YouTube

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

### Próximos passos
- [ ] Dashboard web para monitoramento
- [ ] Integração com n8n para automação agendada
- [ ] Otimização baseada em analytics (feedback loop)
- [ ] Suporte a novos nichos e plataformas
- [ ] Modo persona reativado para TikTok
- [ ] Testes automatizados em CI/CD
- [ ] Containerização (Docker)

---

## Autor

Projeto desenvolvido como estudo e construção de uma plataforma de automação com IA aplicada ao comércio digital e criação de conteúdo.
