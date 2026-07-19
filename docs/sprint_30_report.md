# Sprint 30 — Relatório de Qualidade Editorial

## Setup antes do batch

```bash
cp .env.sprint30.example .env          # Railway: aba Variables
python3 -c "from scripts.ai.router import get_client; import json; print(json.dumps(get_client().health(), indent=2))"
python3 scripts/run_sprint_30_batch.py --max-videos 2   # validação (~15 min)
python3 scripts/run_sprint_30_batch.py --max-videos 8   # batch completo
```

Mínimo obrigatório: **1 chave de IA** + **PEXELS_API_KEY**. TTS: Azure (recomendado) ou fallback Edge/gTTS gratuito.

Preencher após rodar 5–10 vídeos reais em temas diferentes.

## Baseline vs Sprint 30

| Métrica | Baseline | Sprint 30 | Δ |
|---------|----------|-----------|---|
| Relevância visual média/cena (0–100) | | | |
| CTR estimado thumbnail (A/B vencedor) | | | |
| Retenção prevista 30s | | | |
| Retenção prevista 1min | | | |
| Retenção prevista 3min | | | |
| Retenção prevista 6min | | | |
| Trilha + SFX presentes | sim/não | sim/não | |

## Vídeos produzidos

| # | Tema | visual_score médio | thumb variant | CTR est. | retenção est. | áudio OK |
|---|------|-------------------|---------------|----------|---------------|----------|

## O que melhorou

-

## O que não melhorou

-

## Sprint 31 (backlog)

-
