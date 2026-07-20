# Sessão de 20 de julho de 2026 — AI-Commerce-OS

Resumo completo do trabalho realizado nesta sessão, focado na evolução do **Dark Channel Renderer** (pipeline YouTube Dark 16:9 estilo canais BR de mistério).

---

## Problemas identificados e resolvidos

### 1. Vídeos muito curtos (~4 min)
O template de roteiro tinha narrações curtas e durações de cena pequenas (30–45 s), produzindo vídeos abaixo do alvo de ~8 minutos para o formato dark channel.

**Solução:** Expansão das 7 cenas do template com textos dramáticos longos e durações ajustadas (60 s no gancho/conclusão, 90 s nas cenas intermediárias), totalizando ~570 s de timeline visual.

### 2. Narração genérica (Edge TTS apenas)
A narração usava apenas Edge TTS (`pt-BR-FranciscaNeural`), sem controle fino de tom dramático e dependência de serviço externo.

**Solução:** Integração do **Kokoro TTS** como provedor primário (local, gratuito), com velocidade 0.85 para tom mais dramático. Edge TTS permanece como fallback automático se Kokoro falhar.

### 3. Voz Kokoro incorreta para português
A voz inicial configurada era `bf_alice` (inglês), gerando narração inadequada para conteúdo PT-BR.

**Solução:** Troca para `pf_dora` (voz feminina em português), com `pm_alex` documentado como alternativa masculina. Variáveis `KOKORO_VOICE` e `KOKORO_SPEED` adicionadas ao `.env.minimal`.

### 4. Falhas frequentes de imagem (Wikimedia)
O pipeline dependia exclusivamente do Wikimedia Commons; quando a API falhava ou não retornava `.jpg`, a cena caía em gradiente escuro sem imagem real.

**Solução (evolução em duas etapas):**
- Primeiro: fallback em cadeia Wikimedia → query simplificada (2 palavras) → Lorem Picsum.
- Depois (fix final): **Picsum como imagem base garantida**, com tentativa opcional de substituição por foto real do Wikimedia. Reduz drasticamente cenas vazias.

### 5. Legendas difíceis de ler
Fonte grande (52 px), sem caixa de fundo, chunks de 6 palavras — legibilidade ruim em vídeos longos.

**Solução:** Fonte 38 px, caixa semi-transparente (`boxcolor=black@0.4`), chunks de 5 palavras, sincronização proporcional por palavra.

### 6. Música de fundo ausente ou inconsistente
Não havia trilha dedicada; o mix dependia apenas da biblioteca genérica.

**Solução:** Asset `assets/audio/dark_ambient.mp3` adicionado como trilha padrão, mixada a 6% sobre a narração (reduzido de 8% para não competir com a voz).

### 7. Duração de cenas sem verificação
Clips Ken Burns podiam divergir da duração esperada sem log visível.

**Solução:** Logging de `duration`, `frames` no ffmpeg e comparação `actual vs expected` via `probe_duration` após cada clip.

---

## Arquivos criados e modificados

### Criados
| Arquivo | Descrição |
|---------|-----------|
| `scripts/audio/kokoro_tts.py` | Módulo Kokoro TTS com `KPipeline(lang_code="p")` para português |
| `assets/audio/dark_ambient.mp3` | Trilha ambient dark (~4,8 MB) para mix de fundo |

### Modificados
| Arquivo | Alterações principais |
|---------|----------------------|
| `scripts/video/dark_channel_renderer.py` | Pipeline completo: roteiro 8 min, Kokoro+Edge, Picsum+Wikimedia, legendas, música, logs de duração |
| `scripts/video/simple_footage.py` | Fallback Picsum e query simplificada no downloader legado |
| `.env.minimal` | `TTS_PROVIDER=kokoro`, `KOKORO_VOICE=pf_dora`, `KOKORO_SPEED=0.85` |
| `requirements.txt` | Dependências `kokoro>=0.9.4` e `soundfile>=0.12.1` |
| `Dockerfile` | Pacote `espeak-ng` para suporte Kokoro no container |

---

## Estado atual do pipeline

### Dark Channel Renderer (7 passos)

```
Roteiro template (7 cenas)
    ↓
Narração Kokoro TTS (fallback Edge TTS)
    ↓
Imagens Picsum (base) + Wikimedia (substituição opcional) + Ken Burns
    ↓
Legendas queimadas (drawtext, 5 palavras/chunk)
    ↓
Música dark ambient (6%)
    ↓
Color grade escuro
    ↓
Concatenação final (ffmpeg concat + áudio)
```

### Integração com API
- FastAPI (`/api/v1/pipeline/run`) enfileira jobs assíncronos via `main.py`
- Download público em `/pipeline/download/{job_id}` e `/download/latest-video`
- Vídeos salvos em volume persistente (`/app/persistent`)

### Infraestrutura
- Deploy Railway configurado (Docker + `railway.toml`)
- CI GitHub Actions presente (`.github/workflows/ci.yml`)
- Smoke test disponível (`scripts/cloud/smoke_test_railway.py`)
- n8n workflows prontos mas ativação manual pendente

### Pendências conhecidas (fora desta sessão)
- OAuth YouTube no Railway (tokens)
- Volume persistente no Railway Dashboard
- Merge PR #23 para CI ativo no main
- Strategy Engine ainda não integrado ao fluxo TikTok Shop (prioridade arquitetural V1)

---

## O que funciona agora

1. **Geração de vídeo dark channel end-to-end** com roteiro dramático PT-BR de ~8 minutos
2. **Narração Kokoro** em português (`pf_dora`) com fallback automático para Edge TTS
3. **Imagens garantidas** via Lorem Picsum, enriquecidas por Wikimedia quando disponível
4. **Efeito Ken Burns** por cena com duração configurável e verificação pós-render
5. **Legendas legíveis** com caixa de fundo e timing proporcional ao texto
6. **Trilha ambient** mixada automaticamente a 6%
7. **Color grade vintage/escuro** aplicado nas cenas
8. **API REST** para disparar pipeline, consultar status e baixar vídeo
9. **Docker** pronto com dependências Kokoro (`espeak-ng`, `kokoro`, `soundfile`)

### Comando local de teste
```bash
python scripts/test_one_video.py
# ou via API:
python scripts/cloud/gerar_video.py --topic "Seu tema"
```

---

## Próximos passos recomendados para a próxima sessão

1. **Teste E2E em produção (Railway)** — rodar `smoke_test_railway.py` contra URL real e validar Kokoro no container
2. **Sincronizar áudio/vídeo** — alinhar duração dos clips visuais à duração real da narração (hoje o visual é ~570 s fixo; a narração pode ser mais longa)
3. **Melhorar substituição Wikimedia** — filtrar imagens por relevância ao `visual_query` da cena
4. **Thumbnail automática** — gerar thumbnail dark channel a partir do frame do gancho
5. **Upload YouTube OAuth** — configurar tokens no Railway e testar `YOUTUBE_AUTO_UPLOAD=true`
6. **Ativar n8n** — executar `infra/setup_n8n.py` e conectar workflows 01/02/03
7. **Merge PR #23** — ativar CI completo no GitHub Actions
8. **Integrar Strategy Engine** — conectar saída de `generate_creative_strategy` ao Script Engine (prioridade V1 do projeto)

---

## Commits feitos hoje (20/07/2026)

| Hash | Descrição |
|------|-----------|
| `05451d9` | **feat: 8min video, better subtitles, ambient music, image variety** — Roteiro expandido (7 cenas, ~570 s), legendas melhoradas (fonte 38 px, caixa, 5 palavras), trilha `dark_ambient.mp3`, fallback Picsum no footage, mix musical a 6% |
| `65f5c9f` | **feat: kokoro TTS for dramatic narration, edge TTS as fallback** — Novo módulo `kokoro_tts.py`, integração no renderer, deps `kokoro`/`soundfile`, `espeak-ng` no Dockerfile, vars TTS no `.env.minimal` |
| `1edd04e` | **fix: portuguese kokoro voice, picsum primary image, scene duration fix** — Voz `pf_dora` (PT-BR), Picsum como base garantida com Wikimedia opcional, logs de duração Ken Burns e verificação `probe_duration` |

---

*Gerado automaticamente ao final da sessão de 20/07/2026.*
