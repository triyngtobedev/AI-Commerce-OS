# Sprint 30 — Relatório de Validação pós-Fase 1 (PR #31)

**Data:** 2026-07-19  
**Branch:** `cursor/sprint30-e2e-validation-14eb` (PR #31 + #32)  
**Agentes:** [Validação pós-fase 1](https://cursor.com/agents/bc-ebd31a7d-1aba-4440-aa90-e0103a9714eb) · [Validação E2E real (2ª tentativa)](https://cursor.com/agents/bc-ab60edc5-ab4b-47a9-964d-82fd32522e42)

## Setup executado

```bash
git checkout cursor/sprint30-e2e-validation-14eb   # tracking PR #31
cp .env.sprint30.example .env
pip install -r requirements.txt
python3 -m pytest scripts/test_sprint_30.py scripts/ai/test_router.py -q
python3 scripts/run_sprint_30_batch.py --max-videos 2
```

### Ambiente

| Item | Status |
|------|--------|
| Branch Fase 1 (PR #31) | ✅ checkout |
| Dependências Python | ✅ instaladas |
| FFmpeg | ✅ 6.1.1 |
| `.env` com chaves reais | ❌ **não disponível no cloud agent** |
| Cursor Environment (secrets) | ❌ `environment: null` — nenhum secret injetado (2ª tentativa confirmada) |
| Secrets no `printenv` | ❌ `GEMINI_API_KEY`, `GROQ_API_KEY`, `PEXELS_API_KEY` ausentes |
| Railway produção | ✅ online (`d0887f7`, sem Fase 1 ainda) |

### Bug encontrado no template `.env`

Comentários inline (`GEMINI_API_KEY=  # primário`) eram parseados pelo `python-dotenv` como **valor da chave** (`# primário — …`), causando:

1. **Preflight falso-positivo** — `ready_for_batch: true` sem chaves reais
2. **Falha imediata no router** — `UnicodeEncodeError` ao enviar chaves inválidas para Gemini/Groq

**Correção aplicada:** comentários movidos para linhas separadas no `.env.sprint30.example`.

**Validação da correção (2ª tentativa):** com `.env` vazio (template), preflight retorna `ready_for_batch: false` e aborta antes do batch — comportamento correto.

---

## Testes automatizados (pré-requisito Fase 1)

```
26 passed in ~1s
```

Cobertura relevante:

- `gemini_quota.py` — estado compartilhado, métricas, skip visual score quando quota esgotada
- `VISUAL_SCORE_TOP_N=2` default
- `SPRINT30_THUMBNAIL_AB=false` default
- Router fallback Gemini → Groq → OpenRouter

---

## Batch E2E (`--max-videos 2`)

### Resultado

| Métrica | Valor |
|---------|-------|
| Vídeos produzidos | **0/2** |
| `sprint_30_metrics.jsonl` | vazio (nenhum vídeo completou) |
| Logs | `/tmp/sprint30_batch.log` (agente cloud) |
| Duração | ~2s (falha na 1ª chamada IA por tema) |

### Causa raiz

Chaves API não configuradas no ambiente do agente cloud. O batch selecionou 2 temas corretamente, mas falhou em `analyze_topic` com:

```
❌ Falha total: Nenhuma API de IA disponível.
```

### Temas tentados

1. Os Mistérios das Linhas de Nazca
2. O Templo Mais Antigo do Mundo: A Descoberta que Reescreveu a História da Civilização Humana

---

## Validação por critério

### A) Quota

| Pergunta | Status | Nota |
|----------|--------|------|
| Batch 2 vídeos termina sem `RESOURCE_EXHAUSTED`? | ⏳ **pendente** | Requer chaves reais + batch completo |
| Consumo real bate 17–23 chamadas/vídeo? | ⏳ **pendente** | Estimativa teórica abaixo |

**Estimativa teórica (PR #31):**

| Estágio | Chamadas/vídeo (~8 cenas) |
|---------|---------------------------|
| Visual score (TOP_N=2 × 8 cenas) | 16 |
| Thumbnail A/B Gemini | 0 (desativado) |
| Text generation (router) | ~5–7 |
| **Total** | **~17–23** |

Antes: ~76–98/vídeo (TOP_N=8 + thumbnail A/B).

### B) Visual (TOP_N=2)

| Pergunta | Status |
|----------|--------|
| Qualidade mantida com TOP_N=2? | ⏳ pendente E2E |
| Visual score ainda melhora seleção vs heurístico? | ⏳ pendente E2E |

Código validado: fallback heurístico ativo quando quota esgotada (`test_rank_skips_gemini_when_quota_exhausted`).

### C) Thumbnail (hero frame + BrandKit)

| Pergunta | Status |
|----------|--------|
| Thumbnail aceitável via hero + BrandKit? | ⏳ pendente E2E |
| Comparar com thumbnails IA antigas? | ⏳ pendente E2E |

Flag confirmada: `SPRINT30_THUMBNAIL_AB=false`.

### D) Pipeline completo

| Etapa | Status |
|-------|--------|
| Roteiro gerado | ❌ falhou (sem IA) |
| Cenas criadas | ❌ não alcançado |
| Footage-first | ❌ não alcançado |
| Áudio | ❌ não alcançado |
| Legendas | ❌ não alcançado |
| Render final | ❌ não alcançado |
| Upload/export | ⏭️ desabilitado (`auto_upload=false`) |

---

## Métricas Gemini (coleta real)

```json
{}
```

Nenhuma métrica coletada — batch não produziu vídeos.

Campos esperados em `sprint_30_metrics.jsonl` após batch bem-sucedido:

- `gemini_total_calls`
- `gemini_calls_by_stage` (`visual_score`, `thumbnail`, `text_generation`)
- `gemini_calls_by_model`
- `gemini_quota_fallbacks`
- `gemini_quota_exhausted`

---

## Próximo passo para completar validação E2E

### Opção A — Cursor Cloud Agent (recomendado)

1. Abra [cursor.com → Cloud Agents → Secrets](https://cursor.com/dashboard/cloud-agents)
2. Adicione como **Runtime Secret** (ou Environment Variable):
   - `GEMINI_API_KEY`
   - `GROQ_API_KEY`
   - `PEXELS_API_KEY`
3. **Workaround conhecido (jul/2026):** secrets com escopo *Environment* podem não ser injetados. Recrie os mesmos secrets em escopo **Personal** e inicie um agente novo.
4. Opcional: vincule um **Cursor Environment** ao repositório (atualmente `environment: null`).
5. Re-execute o agente com o prompt de validação E2E.

### Opção B — Máquina local / Railway

1. `cp .env.sprint30.example .env` e preencha as chaves (sem comentários inline)
2. ```bash
   python3 scripts/run_sprint_30_batch.py --max-videos 2
   ```
3. Coletar `sprint_30_metrics.jsonl`, vídeos em `output/youtube_dark/`, logs completos

### Coleta pós-batch bem-sucedido

- `sprint_30_metrics.jsonl` — campos Gemini (calls, stages, models, fallbacks)
- Logs completos do batch
- Vídeos em `output/youtube_dark/`
- Preencher tabelas de qualidade abaixo

---

## Baseline vs Sprint 30 (preencher após E2E)

| Métrica | Baseline | Sprint 30 Fase 1 | Δ |
|---------|----------|------------------|---|
| Relevância visual média/cena (0–100) | | | |
| CTR estimado thumbnail | | | |
| Retenção prevista 30s | | | |
| Retenção prevista 1min | | | |
| Retenção prevista 3min | | | |
| Retenção prevista 6min | | | |
| Trilha + SFX presentes | | | |
| Gemini calls/vídeo | ~76–98 | ~17–23 (est.) | |

## Vídeos produzidos

| # | Tema | visual_score médio | thumb variant | CTR est. | retenção est. | áudio OK |
|---|------|-------------------|---------------|----------|---------------|----------|
| — | — | — | hero+BrandKit | — | — | — |

## O que melhorou (Fase 1 — código)

- Quota Gemini centralizada (`gemini_quota.py`)
- Consumo multimodal reduzido (TOP_N 8→2, modelo lite)
- Thumbnail A/B Gemini desativado por default
- Métricas de consumo Gemini no JSONL

## O que não melhorou

- E2E não executado — bloqueado por ausência de API keys no cloud agent

## Sprint 31 (backlog)

- Reavaliar TOP_N=2 vs qualidade visual com dados reais
- Thumbnail A/B opcional com quota guard
- Comparar hero+BrandKit vs variantes IA
