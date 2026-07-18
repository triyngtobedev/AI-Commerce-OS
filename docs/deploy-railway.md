# Deploy na Nuvem — Railway (zero SSH)

Gere vídeos **na nuvem** sem travar o PC. Você roda **um comando** no Windows → o vídeo processa online → o MP4 baixa sozinho.

**Sem SSH. Sem terminal de servidor. Sem DevOps.**

---

## Por que Railway (e não Hetzner)?

| Opção | Veredicto |
|-------|-----------|
| **Railway.app** ✅ | GitHub → deploy automático, painel visual, ~R$ 25/mês |
| Render.com | Jobs longos exigem plano pago caro + timeout |
| Google Cloud Run | Setup complexo, limite de 60 min por request |
| Modal.com | Reescrever pipeline inteiro |
| Replicate.com | Só modelos IA, não o pipeline completo |
| ~~Hetzner~~ | Abandonado — exige SSH e configuração manual |

---

## Como funciona

```
[Seu PC Windows]                    [Railway.app]
       │                                   │
       │  .\scripts\cloud\gerar_video.ps1   │
       │  ───────────────────────────────►  │  API recebe o tema
       │                                    │  FFmpeg + IA (45–120 min)
       │  acompanha progresso...            │
       │  ◄───────────────────────────────  │  vídeo pronto
       │  download automático               │
       ▼                                    ▼
 downloads/video_final.mp4          (processamento na nuvem)
```

Seu PC **não roda FFmpeg, Whisper nem renderização**.

---

## Os 5 passos (faça uma vez)

### 1. Criar conta e conectar o GitHub

1. Acesse [railway.app](https://railway.app) e crie conta (pode usar login com GitHub).
2. Escolha o plano **Hobby** (~US$ 5/mês, cabe no orçamento de R$ 25).
3. Clique **New Project** → **Deploy from GitHub repo** → selecione **AI-Commerce-OS**.
4. Se pedir, autorize o Railway a acessar seu repositório.

### 2. Configurar memória e variáveis

1. No painel Railway, clique no serviço → **Settings** → **Resources** → defina **4 GB RAM** (Whisper + FFmpeg precisam disso).
2. Vá em **Variables** e adicione (copie do seu `.env` local):

| Variável | Obrigatória | Exemplo |
|----------|-------------|---------|
| `PIPELINE_API_KEY` | Sim | gere uma senha longa (veja passo 3) |
| `GEMINI_API_KEY` | Sim | sua chave Google AI |
| `GROQ_API_KEY` | Recomendado | console.groq.com |
| `OPENROUTER_API_KEY` | Recomendado | openrouter.ai/keys — modelos `:free` sem cota diária |
| `PEXELS_API_KEY` | Sim | pexels.com/api — footage lofi_dark |
| `AI_PROVIDER_ORDER` | Opcional | `gemini,openrouter,groq` (padrão). Amanhã: `gemini,groq,openrouter` |
| `WHISPER_MODEL_SIZE` | Recomendado | `tiny` |
| `AZURE_SPEECH_KEY` | Opcional | ou deixe Edge-TTS gratuito |
| `AZURE_SPEECH_REGION` | Opcional | ex: `brazilsouth` |

**PEXELS no Railway:** copie o valor de `PEXELS_API_KEY` do seu `.env` local (obtenha em [pexels.com/api](https://www.pexels.com/api/)) → Railway → serviço → **Variables** → **New Variable** → nome `PEXELS_API_KEY`, valor colado → **Deploy**. Nos Deploy Logs deve aparecer `PEXELS_API_KEY presente: True`.

**OpenRouter no Railway:** mesma chave do `.env` local → variable `OPENROUTER_API_KEY`. Teste local:

```powershell
python scripts/ai/test_openrouter.py
```

3. Aguarde o deploy ficar **Active** (verde) — leva ~5–10 min na primeira vez.

### 3. Copiar URL e chave para o PC

1. No Railway: **Settings** → **Networking** → **Generate Domain** → copie a URL (ex: `https://ai-commerce-os-production.up.railway.app`).
2. Gere uma chave segura no PowerShell do Windows:

```powershell
-join ((1..32) | ForEach-Object { '{0:x2}' -f (Get-Random -Max 256) })
```

3. Use **a mesma chave** em `PIPELINE_API_KEY` no Railway **e** em `CLOUD_API_KEY` no PC.
4. No PC, abra o arquivo `.env` na pasta do projeto e preencha:

```env
CLOUD_API_URL=https://SUA-URL.up.railway.app
CLOUD_API_KEY=a1b2c3d4e5f6...
```

**Atalho interativo:**

```powershell
.\scripts\cloud\configurar_pc.ps1
```

### 4. Testar a conexão

```powershell
python scripts/cloud/gerar_video.py --topic "teste de conexão"
```

Se aparecer `✓ Servidor online`, a API está OK. Esse tema é só ping — pode falhar no score ou render.

Para validar o pipeline completo, use um tema real:

```powershell
python scripts/cloud/gerar_video.py --topic "Os 5 crimes mais perturbadores da história"
```

### 5. Gerar vídeos (uso diário)

```powershell
.\scripts\cloud\gerar_video.ps1 -Topic "A verdade sobre a Biblioteca de Alexandria"
```

Ou com produção completa:

```powershell
.\scripts\cloud\gerar_video.ps1 -Topic "Crimes não resolvidos" -Production
```

O script envia o tema, mostra progresso a cada 30 segundos e salva o MP4 em `downloads/`.

**Tempo típico:** 45–120 minutos. Seu PC fica livre.

### 6. Automação diária com n8n (opcional — zero comandos manuais)

Depois do Railway funcionando, ative a geração automática:

```powershell
.\infra\ativar-n8n.ps1
```

Isso configura o n8n para disparar **1 vídeo por dia às 8h** no Railway, sem você rodar nada.

Guia completo: [`docs/ATIVAR-N8N.md`](docs/ATIVAR-N8N.md)

---

## Custos

| Item | Custo |
|------|-------|
| Railway Hobby | ~US$ 5/mês base + uso (~R$ 25 total) |
| APIs (Gemini, Pexels) | free tiers disponíveis |
| **Total infraestrutura** | **~R$ 25/mês** ✅ |

---

## Problemas comuns

| Problema | Solução |
|----------|---------|
| "Não foi possível conectar" | Confira `CLOUD_API_URL` (com `https://`), deploy Active no Railway |
| 502 / timeout no health check | App deve escutar em `0.0.0.0:$PORT`. Em **Settings → Networking**, confira que **Target Port** coincide com a porta do uvicorn (Deploy Logs mostram `Starting uvicorn on 0.0.0.0:XXXX`) |
| "Invalid X-API-Key" | `CLOUD_API_KEY` no PC = `PIPELINE_API_KEY` no Railway |
| 503 `PIPELINE_API_KEY not configured` | Defina `PIPELINE_API_KEY` no Railway (ou `CLOUD_API_KEY` — mesmo valor). Após deploy, GET `/api/v1/health` deve retornar `"auth_configured": true` |
| Job falha com `GEMINI_API_KEY não encontrada` | Adicione `GEMINI_API_KEY` em Variables (Google AI Studio → Get API Key). Deploy Logs devem mostrar `GEMINI_API_KEY presente: True` |
| Tema descartado por score baixo | Normal para temas genéricos (`teste de conexão`). Use tema real ou injete via API (score ignorado automaticamente) |
| Job falhou / OOM | Confirme 4 GB RAM em Settings → Resources |
| Deploy falhou | Veja **Deploy Logs** no Railway — geralmente falta variável |

---

## Atualizar o código na nuvem

Push no GitHub → Railway redeploya automaticamente. Zero SSH.
