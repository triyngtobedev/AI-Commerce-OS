# Análise de Dark Channels — AI-Commerce-OS

Relatório consolidado das Fases 1–3. Foco: **monetização AdSense rápida** via pipeline `youtube_dark` (Projeto Atlas).

> **nota:** Este documento analisa padrões de canais dark do YouTube para alimentar produção automatizada — não copia ativos protegidos.

---

## Objetivo do projeto (filtro de decisão)

| Critério | Meta |
|----------|------|
| Monetização | AdSense — CTR alto, retenção 8+ min (mid-roll), volume 2–3 vídeos/semana |
| Produção | Faceless: stock + TTS + BrandKit + FFmpeg |
| Nicho | História, mistério, curiosidades, fatos reais |
| Qualidade alvo | 80% da percepção LEMMiNO com 5% do esforço manual |

**Decisão de formato:** documentário narrativo (LEMMiNO) como **primário**; formato lista (Dark5) como **variante de volume** quando o tema se presta a sub-seções numeradas.

---

## Fase 1 — Pesquisa e mapeamento (resumo)

16 referências analisadas em 4 nichos. Apenas padrões aplicáveis ao canal dark de monetização foram mantidos na Fase 2.

### Referências documentais (core do pipeline)

| Canal | Subs (est.) | Padrão-chave | Aplicabilidade |
|-------|-------------|--------------|----------------|
| LEMMiNO | ~4,5M | Ultra-polished, B-roll cinematográfico, 20–40 min, texto mínimo | Referência de qualidade — adaptar para 8 min automatizado |
| Nexpo | ~3M | Mistério unsettling, atmosfera dark, pacing deliberado | Tom e mood visual |
| Dark5 | ~1,5M | Lista numerada, thumbnail com número grande, 5–10 min | Variante de roteiro para volume |
| Be Amazed | ~4M | Pacing rápido, texto bold, retenção alta faceless | Referência de pacing (cortes 15–20s) |

### Referências descartadas para este projeto

| Origem | Motivo |
|--------|--------|
| Fireship, NetworkChuck, Theo | Tech/face-cam — nicho e formato incompatíveis |
| Hormozi, Thomas Frank | Talking head / screencast — não faceless |
| 0x100x, Coin Bureau charts | Estética finance/crypto — quebra posicionamento documental |
| Linear, Algorithm Agency | SaaS B2B — irrelevante para AdSense história |

### Padrões transversais (14/16 canais dark)

1. Fundo escuro sólido (não gradiente decorativo)
2. **1 accent color** apenas
3. **3–5 palavras** no thumbnail
4. Hook nos primeiros **5 segundos**
5. **1 focal point** por thumbnail
6. Contraste **4.5:1+** para mobile
7. Consistência visual cross-vídeo

---

## Fase 2 — Curadoria (classificação)

### ✅ Replicável direto (18 padrões)

Já no pipeline ou plug-and-play:

| # | Padrão | Implementação |
|---|--------|---------------|
| 1 | Paleta navy + gold | `brand_profile.py` |
| 2 | Thumbnail split 42/58 | `brand_kit.compose_thumbnail()` |
| 3 | Máx 4 palavras UPPERCASE | `ThumbnailStyle.hook_max_words` |
| 4 | Barra accent + bússola | `draw_compass_badge()`, accent bar |
| 5 | Shadow 3 camadas | `compose_thumbnail()` linhas 320–323 |
| 6 | Vignette + color grade | `CinematicStyle` |
| 7 | Ken Burns / parallax | `SCENE_MOTION` |
| 8 | Intro/outro cards | `render_intro_card()`, `render_outro_card()` |
| 9 | Lower thirds hook + revelação | `show_lower_third_on` |
| 10 | Watermark 12% | `watermark_opacity` |
| 11 | Capítulos 4–6 | `chapter_builder.py`, prompts |
| 12 | Títulos pergunta/consequência/número | `youtube_content_generation.md` |
| 13 | Descrição SEO estruturada | prompts + `youtube_content.py` |
| 14 | Tags PT + EN | prompts |
| 15 | Comentário fixado | JSON de output |
| 16 | Playlists por subcategoria | `topics_source.json`, topic_research |
| 17 | Cadência 2–3/semana | cron + `youtube_uploader.py` |
| 18 | Consistência visual cross-vídeo | BrandKit centralizado |

### 🔄 Adaptável (10 padrões — alto ROI)

| # | Padrão | Esforço | Impacto |
|---|--------|---------|---------|
| 1 | Pacing Be Amazed (cenas 15–20s) | Médio | Alto — retenção |
| 2 | Formato lista Dark5 | Médio | Médio-alto — volume |
| 3 | Film grain FFmpeg | Baixo | Médio — percepção premium |
| 4 | Gold border thumbnail 2px | Baixo | Médio — visibilidade dark mode YT |
| 5 | Surface ladder overlays | Baixo | Baixo-médio |
| 6 | Soundtrack dark/orchestral | Médio | Alto — retenção |
| 7 | Silêncio dramático TTS | Médio | Médio |
| 8 | Shorts teaser (hook 60s) | Alto | Médio — descoberta |
| 9 | Validação mobile 168px | Baixo | Médio — CTR |
| 10 | Multi-canal por sub-nicho | Alto | Médio — escala pós-1K subs |

### ❌ Descartável (12 padrões)

Face-cam, neon crypto, cyberpunk retro, screencast, glassmorphism pesado, red+black tech, charts como hero, tom humor, volume 300+/semana, community posts manuais, SaaS screenshots, clickbait que não entrega.

---

## Fase 3 — Decisões de implementação

### Formato de conteúdo

```
Primário (80% dos vídeos):  Documentário narrativo LEMMiNO-style
                            8 cenas · 8 min · arco hook→contexto→dev→revelação→impacto

Secundário (20%):           Formato lista Dark5-style
                            "5 fatos sobre X" · sub-seções numeradas · mesmo BrandKit
```

> **nota:** LEMMiNO produz manualmente ~40h/vídeo. O pipeline mira **retenção + percepção premium** via BrandKit, grade cinematográfico e pacing — não perfeição frame-a-frame.

### Conflitos resolvidos

| Conflito | Decisão |
|----------|---------|
| Estética dark vs. legibilidade | **Clareza vence** — texto branco/gold sobre navy; legendas SRT no vídeo |
| LEMMiNO vs. Dark5 | **Narrativo primário** — lista só quando tema permite sub-seções naturais |
| Qualidade vs. volume | **2–3 vídeos/semana** — não 300+/semana (Hormozi) |
| CTR vs. retenção | Títulos fortes OK, mas roteiro **deve entregar** — algoritmo penaliza bait |

---

## Roadmap impacto/esforço

| Ação | Impacto (1–10) | Esforço (1–10) | Prazo | Status |
|------|---------------|----------------|-------|--------|
| Thumbnail split + hook 4 palavras | 10 | 2 | ✅ Feito | `brand_kit.py` |
| Hook 5s + intro card | 9 | 2 | ✅ Feito | pipeline |
| Títulos consequência/pergunta/número | 9 | 3 | ✅ Feito | prompts |
| Color grade + vignette | 8 | 2 | ✅ Feito | `CinematicStyle` |
| Cadência 2–3/semana | 8 | 4 | Semana 1 | cron/uploader |
| Playlists por subcategoria | 7 | 3 | Semana 1 | manual inicial |
| Pacing cenas 15–20s | 8 | 6 | Semana 2 | `scene_timeline` |
| Soundtrack dark/orchestral | 7 | 6 | Semana 2 | `soundtrack_engine` |
| Formato lista Dark5 (roteiro) | 6 | 5 | Semana 3 | novo template prompt |
| Film grain FFmpeg | 5 | 3 | Semana 2 | 1 filtro pós-render |
| Gold border thumbnail | 5 | 2 | Semana 2 | `compose_thumbnail()` |
| Validação mobile 168px | 6 | 3 | Semana 2 | `thumbnail_generator` |
| Shorts teaser automático | 6 | 8 | Mês 2 | pipeline extra |
| Multi-canal sub-nicho | 5 | 9 | Mês 3+ | após 1K subs |

---

## Fontes

- Case studies: [Alan Spicer/Coin Bureau](https://alanspicer.com/coin-bureau-trading-youtube-growth-case-study/), [StartupSpells/Fireship thumbnails](https://startupspells.com/p/algorithms-love-patterns-why-copying-thumbnails-works-on-youtube)
- Thumbnail data: [Hooksnap 2026](https://www.hooksnap.io/blog/youtube-thumbnail-colors-that-get-clicks), [Ventress Playbook 2025](https://ventress.app/blog/2025-youtube-thumbnail-design-playbook/)
- Código: `scripts/core/brand_kit.py`, `scripts/core/brand_profile.py`, `scripts/youtube/thumbnail_generator.py`
- Tokens: `design/tokens-dark.json`
- Copy: `templates/copy-templates.md`
- Guia de produção: `docs/aicommerceos-content-guide.md`

---

## Entregáveis desta análise

| Arquivo | Conteúdo |
|---------|----------|
| `docs/dark-channel-analysis.md` | Este relatório |
| `docs/aicommerceos-content-guide.md` | Guia operacional de produção |
| `design/tokens-dark.json` | Design tokens alinhados ao BrandKit |
| `templates/copy-templates.md` | Templates de título, descrição, CTA, bio |
