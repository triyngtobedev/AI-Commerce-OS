# Configuração OAuth do YouTube

Este guia explica como configurar a autenticação OAuth do YouTube no AI-Commerce-OS para upload automático e acesso ao YouTube Analytics.

## Variáveis de ambiente

O sistema utiliza três variáveis no arquivo `.env`:

| Variável | Descrição |
|----------|-----------|
| `YOUTUBE_CLIENT_ID` | ID do cliente OAuth (Google Cloud Console) |
| `YOUTUBE_CLIENT_SECRET` | Segredo do cliente OAuth |
| `YOUTUBE_REFRESH_TOKEN` | Token de atualização (gerado automaticamente) |

## Pré-requisitos no Google Cloud

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/)
2. Crie ou selecione um projeto
3. Ative as APIs:
   - **YouTube Data API v3**
   - **YouTube Analytics API**
4. Em **APIs e Serviços → Credenciais**, crie credenciais do tipo **ID do cliente OAuth**
5. Tipo de aplicativo: **Aplicativo para computador**
6. Adicione `http://localhost` como URI de redirecionamento autorizado

## Configuração automática (recomendado)

Execute o fluxo OAuth interativo:

```bash
python main.py --youtube-auth
```

O sistema irá:

1. Solicitar `YOUTUBE_CLIENT_ID` e `YOUTUBE_CLIENT_SECRET` (se ausentes)
2. Abrir o navegador para autorização Google
3. Capturar o Authorization Code automaticamente
4. Gerar o Refresh Token
5. Salvar as credenciais no arquivo `.env`
6. Validar a conexão com o canal

## Validação da configuração

Para verificar se as credenciais estão corretas:

```bash
python main.py --youtube-validate
```

A validação verifica:

- Presença das três variáveis
- Formato do Client ID
- Conexão com a YouTube Data API
- Canal associado à conta

## Configuração manual

Se preferir configurar manualmente, copie `.env.example` para `.env` e preencha:

```env
YOUTUBE_CLIENT_ID=seu_id.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=seu_secret
YOUTUBE_REFRESH_TOKEN=seu_refresh_token
```

Para obter o refresh token manualmente, use o fluxo interativo (`--youtube-auth`) — é a forma mais confiável.

## Upload automático

Após configurar as credenciais, publique vídeos automaticamente:

```bash
python main.py --platform youtube_dark --max-videos 1 --upload
```

Ou habilite via `.env` (sem precisar da flag `--upload`):

```env
YOUTUBE_AUTO_UPLOAD=true
```

### Flags de controle

| Variável / Flag | Efeito |
|-----------------|--------|
| `--upload` | Força upload após produção |
| `YOUTUBE_AUTO_UPLOAD=true` | Habilita upload via `.env` |
| `YOUTUBE_DRY_RUN=true` | Bloqueia upload (modo simulação) |
| `YOUTUBE_PUBLISH_ENABLED=false` | Desabilita publicação globalmente |

Quando o upload está desabilitado, o pipeline registra `SKIPPED` nas métricas com o motivo.

## YouTube Analytics

Com as credenciais configuradas, o sistema pode consultar métricas reais do canal:

```bash
python main.py --youtube-analytics
```

Métricas disponíveis:

- CTR (taxa de cliques)
- Retenção média
- Tempo médio de exibição
- Impressões
- Visualizações
- Crescimento de inscritos

Esses dados alimentam recomendações de otimização para títulos, descrições, tags, thumbnails e estratégia de conteúdo.

## Solução de problemas

### "YOUTUBE_CLIENT_ID — ausente ou não configurado"

Execute `python main.py --youtube-auth` ou preencha manualmente o `.env`.

### "Refresh token inválido ou expirado"

1. Revogue o acesso em [Permissões da conta Google](https://myaccount.google.com/permissions)
2. Execute novamente: `python main.py --youtube-auth`

### "Nenhum canal encontrado"

Certifique-se de autorizar com a conta Google que possui o canal YouTube.

### "google-auth-oauthlib não instalado"

```bash
pip install google-api-python-client google-auth-oauthlib
```

## Escopos OAuth utilizados

- `youtube.upload` — publicação de vídeos e thumbnails
- `youtube.readonly` — leitura de dados do canal
- `youtube.force-ssl` — atualização de banner e descrição do canal
- `yt-analytics.readonly` — métricas do YouTube Analytics

## Branding do canal

Gera e aplica identidade visual (banner, descrição):

```bash
# Gerar assets (perfil, banner, descrição)
python main.py --youtube-branding

# Aplicar banner e descrição via API
python main.py --youtube-branding --apply
```

**Importante:** a aplicação via API requer o escopo `youtube.force-ssl`. Se o token foi gerado antes dessa atualização, reautorize:

```bash
python main.py --youtube-auth
```

A **foto de perfil** não pode ser alterada via API (é vinculada à conta Google). Aplique manualmente em YouTube Studio → Personalização.

Assets gerados em `assets/brand/`.

## Arquitetura

| Módulo | Responsabilidade |
|--------|------------------|
| `scripts/publisher/youtube_auth.py` | OAuth, validação, fluxo interativo |
| `scripts/publisher/youtube_uploader.py` | Upload de vídeos |
| `scripts/publisher/youtube_channel_branding.py` | Banner e descrição do canal |
| `scripts/youtube/channel_assets.py` | Geração de assets visuais |
| `scripts/youtube/youtube_analytics.py` | Métricas e insights de otimização |
