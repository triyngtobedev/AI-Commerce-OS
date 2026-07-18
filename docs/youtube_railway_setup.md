# YouTube OAuth no Railway — guia simples

Este guia explica como configurar upload automático e analytics **no Railway**, sem rodar nada no PC depois da configuração inicial.

## Resumo em 4 passos

1. Criar credenciais OAuth no Google Cloud Console
2. Gerar o **refresh token** uma vez (no PC)
3. Colar as 4 variáveis no Railway
4. Pronto — upload e analytics rodam sozinhos no Railway

---

## Passo 1 — Google Cloud Console

1. Acesse [console.cloud.google.com](https://console.cloud.google.com/)
2. Crie ou selecione um projeto
3. Vá em **APIs e Serviços → Biblioteca** e ative:
   - **YouTube Data API v3**
   - **YouTube Analytics API**
4. Vá em **APIs e Serviços → Credenciais**
5. Clique **Criar credenciais → ID do cliente OAuth**
6. Tipo: **Aplicativo para computador**
7. Em **URIs de redirecionamento autorizados**, adicione: `http://localhost`
8. Copie o **Client ID** e o **Client Secret**

---

## Passo 2 — Gerar o Refresh Token (uma vez só)

No seu PC, com o repositório clonado:

```bash
# 1. Copie .env.example para .env
cp .env.example .env

# 2. Cole no .env:
#    YOUTUBE_CLIENT_ID=seu_id.apps.googleusercontent.com
#    YOUTUBE_CLIENT_SECRET=seu_secret

# 3. Rode o fluxo OAuth (abre o navegador)
python main.py --youtube-auth
```

O que acontece:
- O navegador abre pedindo permissão para acessar seu canal YouTube
- Você autoriza com a conta Google do canal
- O script salva automaticamente o `YOUTUBE_REFRESH_TOKEN` no `.env`

**Copie os 3 valores do .env:**
```
YOUTUBE_CLIENT_ID=...
YOUTUBE_CLIENT_SECRET=...
YOUTUBE_REFRESH_TOKEN=...
```

> O refresh token **não expira** enquanto você não revogar o acesso em [myaccount.google.com/permissions](https://myaccount.google.com/permissions).

---

## Passo 3 — Variáveis no Railway

No [railway.app](https://railway.app) → seu projeto → **Variables**, adicione:

| Variável | Valor |
|----------|-------|
| `YOUTUBE_AUTO_UPLOAD` | `true` |
| `YOUTUBE_CLIENT_ID` | (copiado do .env) |
| `YOUTUBE_CLIENT_SECRET` | (copiado do .env) |
| `YOUTUBE_REFRESH_TOKEN` | (copiado do .env) |
| `UPLOAD_VISIBILITY` | `unlisted` (não listado — padrão seguro) |

O Railway redeploya automaticamente. A partir daí, **tudo roda na nuvem**.

---

## Passo 4 — Testar

### Upload automático (via pipeline)

```bash
curl -X POST https://SEU-APP.up.railway.app/api/v1/pipeline/run \
  -H "X-API-Key: SUA_PIPELINE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"platform": "youtube_dark", "production": true, "upload": true, "topic": "teste upload"}'
```

Quando o job completar, o vídeo aparece no YouTube como **não listado** e o link é salvo em `database/videos.json`.

### Upload manual (via API — usado pelo n8n)

```bash
curl -X POST https://SEU-APP.up.railway.app/api/v1/youtube/upload \
  -H "X-API-Key: SUA_PIPELINE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"job_id": "UUID-DO-JOB-CONCLUIDO"}'
```

### Analytics

```bash
# Sincronizar métricas
curl -X POST "https://SEU-APP.up.railway.app/api/v1/analytics/sync" \
  -H "X-API-Key: SUA_PIPELINE_API_KEY"

# Gerar relatório semanal
curl -X POST "https://SEU-APP.up.railway.app/api/v1/analytics/report?days=7" \
  -H "X-API-Key: SUA_PIPELINE_API_KEY"
```

---

## Fluxo completo (Railway + n8n)

```
n8n (domingo 8h) → POST /pipeline/run → Railway gera vídeo
                   → polling status → completed
                   → POST /youtube/upload (idempotente)
                   → link do vídeo salvo

n8n (domingo 9h) → POST /analytics/report → relatório em reports/
```

---

## Problemas comuns

| Erro | Solução |
|------|---------|
| `Credenciais não configuradas` | Verifique as 3 vars OAuth no Railway |
| `Refresh token inválido` | Revogue em myaccount.google.com/permissions e rode `--youtube-auth` de novo |
| `403 thumbnail` | Verifique o canal em youtube.com/verify |
| Upload duplicado | Normal — o sistema é idempotente por job_id |

---

## Arquivos relevantes

| Arquivo | Função |
|---------|--------|
| `scripts/youtube/uploader.py` | Upload + registro em database/videos.json |
| `scripts/analytics/youtube_analytics.py` | Sync métricas → database/analytics.json |
| `scripts/analytics/report.py` | Relatório semanal |
| `api/routers/youtube.py` | Endpoint HTTP para n8n |
| `api/routers/analytics.py` | Endpoint HTTP para relatórios |
