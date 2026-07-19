# Caminho imediato — guia para vibe coder

Passo a passo na ordem certa. Cada etapa depende da anterior em produção.

**Painel visual interativo:** abra [`painel-projeto.html`](painel-projeto.html) no navegador (duplo clique no arquivo).

---

## 1. Merge do PR #23 → ativa CI no GitHub

**O que isso faz:** coloca no `main` os scripts de teste, CI, volume persistente e dashboard.

### Como fazer

1. Abra o PR no GitHub: https://github.com/triyngtobedev/AI-Commerce-OS/pull/23
2. Revise os arquivos (opcional) e clique em **Merge pull request**
3. Confirme o merge
4. Vá em **Actions** no repositório — deve aparecer o workflow **CI** rodando no `main`

### Como saber que deu certo

- Badge verde no workflow CI
- Arquivos novos no `main`: `.github/workflows/ci.yml`, `scripts/cloud/smoke_test_railway.py`, etc.

---

## 2. Smoke test Railway → confirma produção saudável

**O que isso faz:** testa se a API na nuvem responde, bloqueia requests sem chave e aceita jobs.

### Pré-requisitos

- URL do Railway (ex.: `https://ai-commerce-os-production-b4f9.up.railway.app`)
- `PIPELINE_API_KEY` copiada do Railway → Variables

### Como fazer (Windows PowerShell)

```powershell
cd C:\Projetos\AI-Commerce-OS
git pull

# Só health + auth (rápido, não dispara vídeo)
python scripts/cloud/smoke_test_railway.py `
  --url https://SUA-URL.up.railway.app `
  --key SUA_PIPELINE_API_KEY `
  --skip-job
```

Para teste completo (dispara job real — demora e gasta crédito):

```powershell
python scripts/cloud/smoke_test_railway.py `
  --url https://SUA-URL.up.railway.app `
  --key SUA_PIPELINE_API_KEY
```

### Como saber que deu certo

- Mensagem final: **Railway OK — pronto para produção**
- `GET /api/v1/health` retorna `auth_configured: true`

### Alternativa: GitHub Actions

1. No GitHub → **Actions** → **Railway Smoke Test** → **Run workflow**
2. Informe a URL do Railway
3. Configure o secret `PIPELINE_API_KEY` em Settings → Secrets

---

## 3. Volume em `/app/persistent` → jobs não somem no restart

**O que isso faz:** SQLite (`pipeline_jobs.db`) e vídeos em `output/` sobrevivem a redeploy.

### Como fazer

1. Abra [railway.app](https://railway.app) → seu projeto → serviço **ai-commerce-os**
2. **Settings** → **Volumes** → **Add Volume**
3. **Mount path:** `/app/persistent`
4. **Size:** mínimo 5 GB
5. **Save** (o serviço reinicia)

Variáveis opcionais (o entrypoint já define defaults se o volume existir):

```
DATABASE_PATH=/app/persistent/database/pipeline_jobs.db
OUTPUT_DIR=/app/persistent/output
REPORTS_DIR=/app/persistent/reports
```

### Como saber que deu certo

Rode o smoke test de novo (passo 2). No health check:

```json
"persistent_storage": true
```

Guia completo: [railway-volume.md](railway-volume.md)

---

## 4. OAuth YouTube no Railway → upload automático funciona

**O que isso faz:** permite publicar vídeos no YouTube após o pipeline terminar.

### Parte A — Gerar tokens no PC (uma vez)

```powershell
cd C:\Projetos\AI-Commerce-OS
python scripts/youtube/gerar_token.py
```

Ou: `python main.py --youtube-auth`

Siga o navegador Google. O script grava credenciais em `.env.youtube` ou `.env`.

### Parte B — Copiar para o Railway

No Railway → **Variables**, adicione:

```
YOUTUBE_CLIENT_ID=...
YOUTUBE_CLIENT_SECRET=...
YOUTUBE_REFRESH_TOKEN=...
YOUTUBE_AUTO_UPLOAD=true
YOUTUBE_DRY_RUN=false
```

### Como saber que deu certo

- Pipeline completa com upload → vídeo aparece no YouTube (ou unlisted, conforme config)
- Sem erro `invalid_grant` nos logs do Railway

Guia completo: [youtube_oauth.md](youtube_oauth.md)

---

## 5. Ativar n8n → automação diária

**O que isso faz:** n8n dispara o pipeline todo dia (8h) sem você rodar comandos manualmente.

### Pré-requisitos

- Docker Desktop aberto (ícone da baleia na bandeja)
- `.env` com `CLOUD_API_URL` e `PIPELINE_API_KEY`
- Railway Active (passos 2–4 OK)

### Como fazer (Windows — recomendado)

```powershell
cd C:\Projetos\AI-Commerce-OS
.\infra\ativar-n8n.ps1
```

### Alternativa (Python cross-platform)

```powershell
# Validar conexão Railway + credenciais
python infra/setup_n8n.py --validate

# Setup completo (owner, credenciais, import workflows)
python infra/setup_n8n.py
```

### Como saber que deu certo

- n8n abre em http://localhost:5678
- Workflows 01, 02 e 03 importados e **ativos** (toggle verde)
- Teste manual do workflow 01 dispara job no Railway

Guia completo: [ATIVAR-N8N.md](ATIVAR-N8N.md)

---

## 6. Colar notificações nos workflows 01 e 03

**O que isso faz:** avisa no Telegram, Slack ou e-mail quando o pipeline termina ou falha.

### Como fazer

1. Abra `infra/n8n_workflows/notification_nodes.json`
2. Escolha **um canal** (Telegram **ou** Slack **ou** Email)
3. No n8n (http://localhost:5678):
   - Abra workflow **01_pipeline_trigger**
   - Delete o nó **PLACEHOLDER** de notificação (sucesso e falha)
   - Adicione nó Telegram/Slack copiando os parâmetros do JSON
   - Configure credencial (Bot Token Telegram, etc.)
   - Repita no workflow **03_weekly_analytics_report** (e-mail semanal)
4. Salve e mantenha o workflow **ativo**

### Variáveis no n8n (Settings → Variables)

| Canal | Variáveis |
|-------|-----------|
| Telegram | `TELEGRAM_CHAT_ID` + credencial Bot Token |
| Slack | `SLACK_CHANNEL_ID` + credencial Slack Bot |
| Email | `EMAIL_FROM`, `EMAIL_TO` + credencial SMTP |

### Como saber que deu certo

- Dispare um job de teste → mensagem chega no canal escolhido
- Nos JSONs do repo, os nós PLACEHOLDER foram substituídos no n8n (não no arquivo — a edição é na UI)

---

## Checklist rápido

| # | Etapa | Feito? |
|---|-------|--------|
| 1 | PR #23 merged | ☐ |
| 2 | Smoke test OK | ☐ |
| 3 | Volume `/app/persistent` | ☐ |
| 4 | OAuth YouTube no Railway | ☐ |
| 5 | n8n ativo | ☐ |
| 6 | Notificações configuradas | ☐ |

---

## Comandos úteis depois de tudo ativo

```powershell
# Ver dashboard local (jobs, analytics, n8n)
python scripts/dashboard/generator.py --open

# Validar ffmpeg, tokens e providers
python scripts/validate_providers.py

# Rodar testes
python run_tests.py fast
```
