# Ativar automação n8n — guia simples

Este guia é para **você, dono do projeto**, sem precisar entender código.

## O que isso faz?

Depois de ativar, o sistema **gera vídeos sozinho, todo dia**, na nuvem (Railway):

```
[Seu PC com Docker]          [Railway — nuvem]
       │                              │
       │  n8n dispara todo dia 8h     │
       │  ─────────────────────────►  │  pipeline roda sozinho
       │                              │  (45–120 min por vídeo)
       │  n8n acompanha o progresso   │
       │  ◄──────────────────────────  │  vídeo pronto
       ▼                              ▼
  Você não precisa              Tema novo escolhido
  rodar nenhum comando          automaticamente (research)
```

**Você não roda `gerar_video.py` manualmente.** O n8n faz isso por você.

---

## Pré-requisitos (faça uma vez)

| # | O que | Como saber se está OK |
|---|-------|----------------------|
| 1 | **Docker Desktop** instalado e aberto | Ícone da baleia na bandeja do Windows |
| 2 | **Railway** com deploy Active | [docs/deploy-railway.md](deploy-railway.md) |
| 3 | **`.env`** na pasta do projeto preenchido | `CLOUD_API_URL` e `PIPELINE_API_KEY` |

### Variáveis obrigatórias no `.env` (raiz do projeto)

```env
CLOUD_API_URL=https://SUA-URL.up.railway.app
PIPELINE_API_KEY=sua_chave_secreta_aqui
```

> A mesma `PIPELINE_API_KEY` deve estar no painel Railway (Variables).

Se ainda não configurou o Railway, siga primeiro: **[docs/deploy-railway.md](deploy-railway.md)**

---

## Ativação em 1 comando

Abra o **PowerShell** na pasta do projeto e rode:

```powershell
.\infra\ativar-n8n.ps1
```

O script faz tudo sozinho:

1. Cria `infra/.env.n8n` (se não existir)
2. Aponta o n8n para a URL do Railway
3. Sobe o n8n no Docker
4. Importa e ativa os workflows
5. Testa a conexão com o Railway

---

## Depois de ativar

| Item | Valor |
|------|-------|
| Painel n8n | http://localhost:5678 |
| Login n8n | `admin@local.dev` / `n8nLocal!2026` |
| Horário automático | **Todo dia às 8h** (horário de Brasília) |
| O que acontece | 1 vídeo YouTube Dark com tema novo |

### Manter o PC ligado?

Sim — o n8n roda no seu PC via Docker. No horário agendado (8h), ele dispara o Railway.

> **Dica:** Se o PC estiver desligado às 8h, o vídeo **não** será gerado naquele dia. Deixe o PC ligado ou configure o Windows para não hibernar à noite.

---

## Conferir se está funcionando

### 1. n8n online?

Abra http://localhost:5678 no navegador. Deve aparecer o painel do n8n.

### 2. Workflow ativo?

No n8n → **Workflows** → **01 — Pipeline Trigger** → toggle verde (Active).

### 3. Teste manual (sem esperar 8h)

No n8n, abra o workflow **01 — Pipeline Trigger** → clique **Execute workflow**.

Aguarde ~30s e veja se aparece `job_id` no resultado. Depois confira no Railway (Deploy Logs) se o pipeline iniciou.

### 4. Teste via script (alternativa)

```powershell
python scripts/cloud/gerar_video.py --topic "teste de conexão"
```

Se retornar `✓ Servidor online`, o Railway está OK.

---

## Problemas comuns

| Problema | Solução |
|----------|---------|
| "Docker não encontrado" | Abra o Docker Desktop e espere ficar verde |
| "CLOUD_API_URL ausente" | Preencha no `.env` (passo 3 do deploy-railway) |
| "PIPELINE_API_KEY ausente" | Gere uma chave e coloque no `.env` **e** no Railway |
| Workflow não dispara | Confira se o toggle está **Active** (verde) |
| Erro 401 no workflow | `PIPELINE_API_KEY` no `.env` ≠ Railway — devem ser iguais |
| PC desligado às 8h | Vídeo não gera naquele dia — deixe PC ligado |
| n8n parou após reiniciar PC | Rode `.\infra\start-local.ps1` ou `.\infra\ativar-n8n.ps1` de novo |

---

## Parar / reiniciar o n8n

```powershell
# Parar
cd infra
docker compose -f docker-compose.local.yml down

# Reiniciar
.\infra\start-local.ps1
```

---

## Quer mudar o horário?

1. Abra http://localhost:5678
2. Workflows → **01 — Pipeline Trigger**
3. Clique no nó **Schedule Trigger**
4. Altere hora/minuto
5. Salve e mantenha **Active**

---

## Próximo nível (opcional)

- **Notificações Slack/Telegram** quando o vídeo ficar pronto — configure nos nós finais do workflow 01
- **Orquestração de cenas IA via n8n** (workflow 02) — requer n8n acessível pela internet; por padrão as cenas rodam direto no Railway

Documentação técnica completa: [docs/n8n_integration.md](n8n_integration.md)
