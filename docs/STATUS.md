# Status do Projeto — AI-Commerce-OS

> Atualizado em: **19 de julho de 2026**

## Painel visual (vibe coder)

Abra no navegador (duplo clique):

- **[docs/painel-projeto.html](painel-projeto.html)** — snapshot interativo com os 10+ passos clicáveis
- **[docs/CAMINHO-IMEDIATO.md](CAMINHO-IMEDIATO.md)** — guia passo a passo com comandos copy-paste

---

## Resumo

Plataforma de automação com IA para vídeos **YouTube Dark** (16:9) e pipeline legado **TikTok Shop** (9:16). Foco ativo: canal dark + deploy Railway + n8n.

| Área | Status | Notas |
|------|--------|-------|
| Pipeline YouTube Dark | ✅ Funcional | Roteiro, cenas, TTS, render, thumbnail |
| Template lofi_dark | ✅ Funcional local | 1200s, Pexels + FFmpeg fallback |
| Pipeline TikTok Shop | ✅ Legado funcional | Não é o foco da sprint atual |
| VideoGenerator (IA) | ✅ | Kling → fal → Replicate Wan → HF Wan2.2 |
| API FastAPI (`/api/v1`) | ✅ | Jobs assíncronos, health, download |
| Deploy Railway (Docker) | ⚠️ Parcial | Infra pronta; **smoke test + volume pendentes** |
| Upload YouTube OAuth | ⚠️ Parcial | Código OK; **tokens no Railway pendentes** |
| Integração n8n | ⚠️ Parcial | Workflows prontos; **ativação + notificações pendentes** |
| Dashboard web | ✅ | `scripts/dashboard/generator.py` → `output/dashboard.html` |
| CI/CD GitHub Actions | ✅ | PR #23 — merge pendente para ativar no `main` |
| Cobertura de testes | ✅ | `run_tests.py` (pytest, suites modulares) |
| Volume persistente Railway | ⚠️ Código pronto | Config manual no Railway Dashboard |
| Notificações n8n | ⏳ | `notification_nodes.json` — colar na UI |
| Sprint 2 TikTok Shop | ⏳ Backlog | Pesquisa de produtos não priorizada |

---

## Caminho imediato (ordem recomendada)

| # | Etapa | Código | Ação manual |
|---|-------|--------|-------------|
| 1 | Merge PR #23 | ✅ | Merge no GitHub |
| 2 | Smoke test Railway | ✅ `smoke_test_railway.py` | Rodar contra URL real |
| 3 | Volume `/app/persistent` | ✅ entrypoint + health | Add Volume no Railway |
| 4 | OAuth YouTube no Railway | ✅ `gerar_token.py` | Copiar vars para Railway |
| 5 | Ativar n8n | ✅ `ativar-n8n.ps1` / `setup_n8n.py` | Docker + executar script |
| 6 | Notificações Slack/TG | ✅ `notification_nodes.json` | Colar nos workflows 01/03 |

Detalhes: [CAMINHO-IMEDIATO.md](CAMINHO-IMEDIATO.md)

---

## Deploy na nuvem

- **Plataforma:** [Railway.app](https://railway.app)
- **URL de produção:** `https://ai-commerce-os-production-b4f9.up.railway.app`
- **Guias:** [deploy-railway.md](deploy-railway.md) · [railway-volume.md](railway-volume.md)
- **Smoke test:** `python scripts/cloud/smoke_test_railway.py --url URL --key CHAVE --skip-job`
- **Cliente local:** `python scripts/cloud/gerar_video.py --topic "Seu tema"`

Health check expõe:

```json
{
  "status": "ok",
  "auth_configured": true,
  "git_commit": "...",
  "persistent_storage": true
}
```

---

## Automação n8n

- **Ativar:** `.\infra\ativar-n8n.ps1` (Windows) ou `python infra/setup_n8n.py`
- **Validar Railway:** `python infra/setup_n8n.py --validate`
- **Guia:** [ATIVAR-N8N.md](ATIVAR-N8N.md)
- **Notificações:** substituir PLACEHOLDER nos workflows usando [notification_nodes.json](../infra/n8n_workflows/notification_nodes.json)

---

## Testes e qualidade

```bash
python run_tests.py fast          # CI usa esta suite
python run_tests.py               # suite padrão
python run_tests.py cov           # cobertura HTML
python scripts/validate_providers.py
python scripts/fix_requirements_encoding.py
```

| Teste | Resultado |
|-------|-----------|
| Suite rápida (`run_tests.py fast`) | ✅ 46 passed |
| CI GitHub Actions | ⏳ Ativo após merge PR #23 |
| Railway smoke E2E | ⏳ Aguardando execução manual |

---

## Estrutura relevante (jul/2026)

```
api/                          # FastAPI bridge
scripts/cloud/                # entrypoint, smoke test, gerar_video
scripts/dashboard/            # generator.py (dashboard HTML/JSON)
scripts/validate_providers.py # ffmpeg + tokens
infra/n8n_workflows/          # 01, 02, 03 + notification_nodes.json
.github/workflows/            # ci.yml, railway-smoke.yml
docs/painel-projeto.html      # painel visual interativo
docs/CAMINHO-IMEDIATO.md      # guia passo a passo
docs/railway-volume.md        # volume persistente
```

---

## PR em aberto

- **#23** — infra Railway, CI, testes, dashboard expandido  
  https://github.com/triyngtobedev/AI-Commerce-OS/pull/23
