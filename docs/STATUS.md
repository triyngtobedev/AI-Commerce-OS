# Status do Projeto — AI-Commerce-OS

> Atualizado em: **18 de julho de 2026**

## Resumo

Plataforma funcional de automação com IA para produção de vídeos **TikTok Shop** (9:16) e **YouTube Dark** (16:9). Pipeline end-to-end local + API HTTP + deploy na nuvem via Railway.

| Área | Status |
|------|--------|
| Pipeline TikTok Shop | ✅ Funcional |
| Pipeline YouTube Dark | ✅ Funcional (roteiro, cenas, TTS, render, thumbnail) |
| VideoGenerator (IA) | ✅ Kling Web → fal Kling 2.6 → Replicate Wan 2.6 → HF Wan2.2 |
| Upload YouTube OAuth | ✅ Funcional |
| API FastAPI (`/api/v1`) | ✅ Jobs assíncronos, health, download |
| Deploy Railway (Docker) | ✅ Dockerfile + `railway.toml` — ver [deploy-railway.md](deploy-railway.md) |
| Cliente nuvem (`gerar_video.py`) | ✅ Envia tema, faz polling, baixa MP4 |
| Integração n8n | ✅ Pronta — ativar com `infra/ativar-n8n.ps1` (ver [ATIVAR-N8N.md](ATIVAR-N8N.md)) |
| Dashboard web | ⏳ Planejado |
| CI/CD automatizado | ⏳ Planejado |

## Deploy na nuvem

- **Plataforma recomendada:** [Railway.app](https://railway.app) (~R$ 25/mês, 4 GB RAM)
- **URL de produção:** `https://ai-commerce-os-production-b4f9.up.railway.app`
- **Guia:** [docs/deploy-railway.md](deploy-railway.md)
- **Comando local:** `python scripts/cloud/gerar_video.py --topic "Seu tema"`

Correção recente (commit `9deab98`): bind uvicorn em `0.0.0.0:$PORT`, entrypoint LF, alias `/health`.

## Testes recentes

| Teste | Resultado | Detalhes |
|-------|-----------|----------|
| VideoGenerator CLI | ✅ | Replicate Wan 2.6, 1280×720, ~147s — [analysis/test_results.md](../analysis/test_results.md) |
| Railway health | 🔄 | Aguardando redeploy pós-fix de porta |
| Testes unitários YouTube | ✅ | `scripts/youtube/test_*.py` |
| Testes VideoGenerator | ✅ | `tests/test_video_generator.py`, `tests/test_video_apis.py` |

## Estrutura nova (jul/2026)

```
api/                    # FastAPI bridge (pipeline HTTP)
scripts/cloud/          # Cliente nuvem + entrypoint Railway
Dockerfile              # Imagem de produção
railway.toml            # Config Railway (health, startCommand)
infra/docker-compose.cloud.yml
docs/deploy-railway.md
docs/deploy-nuvem.md
```

## Próximos passos

1. Confirmar health check Railway após redeploy (`/api/v1/health`)
2. Validar geração completa na nuvem com `gerar_video.py`
3. Ativar automação n8n (`infra/ativar-n8n.ps1`) para geração diária no Railway
4. Dashboard web e CI/CD
