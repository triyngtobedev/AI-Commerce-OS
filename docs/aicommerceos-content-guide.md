# Guia de Conteúdo — Projeto Atlas (YouTube Dark)

Guia operacional para produção automatizada via AI-Commerce-OS. Use com o pipeline `youtube_dark`.

> **nota:** Prioridade = monetização AdSense (8+ min, mid-roll, CTR, retenção). Documentário narrativo primário; lista numerada como variante.

---

## 1. Design system dark

Tokens completos em [`design/tokens-dark.json`](../design/tokens-dark.json). Resumo visual:

| Token | Hex | Uso |
|-------|-----|-----|
| `background.default` | `#080C18` | Fundo vídeo, footer thumbnail |
| `background.panel` | `#080818` | Painel esquerdo thumbnail |
| `background.elevated` | `#0C1220` | Cards intro/outro, gradiente |
| `accent.gold` | `#FFB703` | Barra topo, underlines, lower thirds |
| `text.primary` | `#FFFFFF` | Hook thumbnail, títulos |
| `text.muted` | `#B4B9C3` | Tagline, subtítulos |
| `border.accent` | `#FFB703` 2px | Borda anti-dark-mode (adaptável) |

**Tipografia:** Roboto Bold (display/hook), Roboto Regular (corpo). Alternativa editorial: Playfair Display só em cards intro.

**Proporção luz/sombra:** 70% sombra / 30% luz. Color grade: `contrast=1.08, brightness=-0.03, saturation=1.08`.

**Elemento de marca:** bússola com letra "A" — canto superior direito do painel thumbnail; centro dos cards intro/outro.

---

## 2. Guia de thumbnails

### Layout A — Split documentário (PADRÃO)

Usado em 80% dos vídeos. Implementado em `brand_kit.compose_thumbnail()`.

```
┌─────────────────────────────────────────────────────────────┐
│▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│ ← accent bar 6px gold
│ PAINEL ESCURO (42%)          │░░│  HERO IMAGE (58%)          │
│                              │░░│                             │
│  SEM CRATERA                 │░░│  [stock footage dramático]  │
│  ─────────                   │░░│                             │
│  1908 | NINGUÉM SABE         │░░│                             │
│                              │░░│                    ⊕ bússola│
│                              │░░│                             │
│▓▓▓ PROJETO ATLAS ▓▓▓▓▓▓▓▓▓▓▓▓▓▓│░░│▓▓▓ História · Mistério ▓▓▓▓▓│
└─────────────────────────────────────────────────────────────┘
  ░░ = gradiente blend 80px
```

**Hierarquia visual:** (1) hook 4 palavras, (2) hero image dramática, (3) barra accent + bússola.

**Regras:**
- Máx 4 palavras, UPPERCASE, 2 linhas, 14 chars/linha
- Hero image de cenas `hook`, `revelacao` ou `impacto` (via `THUMBNAIL_SCENE_PRIORITY`)
- Shadow 3 camadas no texto
- Negative space ~42% no painel — não adicionar clutter
- Testar legibilidade em **168px** (preview mobile)

**Proibido:** faces de apresentador, logos tech, charts, mais de 1 focal point, texto >4 palavras.

---

### Layout B — Lista numerada (Dark5)

Usar quando roteiro = formato "N fatos/coisa". Mesmo BrandKit, variação compositiva.

```
┌─────────────────────────────────────────────────────────────┐
│▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│
│ PAINEL ESCURO (42%)          │░░│  HERO IMAGE (58%)          │
│                              │░░│                             │
│         ┌────┐               │░░│                             │
│         │ 5  │  ← número     │░░│  [imagem evocativa]         │
│         └────┘    gold 120px │░░│                             │
│                              │░░│                             │
│  FATOS SOBRE                 │░░│                    ⊕ bússola│
│  GUERRA EMUS                 │░░│                             │
│                              │░░│                             │
│▓▓▓ PROJETO ATLAS ▓▓▓▓▓▓▓▓▓▓▓▓▓▓│░░│▓▓▓ História · Mistério ▓▓▓▓▓│
└─────────────────────────────────────────────────────────────┘
```

**Quando usar:** temas com sub-seções naturais (5 mistérios, 3 teorias, 7 fatos). Acelera produção e CTR previsível.

---

### Layout C — Data shock (consequência)

Variação do Layout A com ênfase em ano/número na linha 2.

```
┌─────────────────────────────────────────────────────────────┐
│▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│
│ PAINEL ESCURO (42%)          │░░│  HERO IMAGE (58%)          │
│                              │░░│                             │
│  O QUE FOI                   │░░│                             │
│  ISSO?                       │░░│  [explosão / evento]        │
│  ─────────                   │░░│                             │
│  1908 | SIBÉRIA              │░░│                    ⊕ bússola│
│                              │░░│                             │
│▓▓▓ PROJETO ATLAS ▓▓▓▓▓▓▓▓▓▓▓▓▓▓│░░│▓▓▓ História · Mistério ▓▓▓▓▓│
└─────────────────────────────────────────────────────────────┘
```

**Quando usar:** eventos datados, explosões, desaparecimentos. Fórmula de título #1 (`{Ano} | {Consequência}`).

---

## 3. Framework de roteiro

### Estrutura base (8 cenas — ~8 min)

Arco narrativo LEMMiNO-style. Mapeamento em `SCENE_MOTION` e prompts `youtube_script_generation.md`.

| Cena | Tipo | Duração alvo | Palavras | Função |
|------|------|-------------|----------|--------|
| 1 | hook | 0:00–0:30 | 50–80 | Pergunta/afirmação chocante — retenção 5s |
| 2 | contexto | 0:30–1:30 | 200–250 | Mundo antes do evento |
| 3–4 | desenvolvimento | 1:30–4:30 | 500–700 | Narrativa principal, fatos, tensão crescente |
| 5 | revelacao | 4:30–5:30 | 200–250 | Twist, teoria, dado surpreendente |
| 6 | consequencias | 5:30–6:30 | 200–250 | Impacto histórico/contemporâneo |
| 7 | impacto | 6:30–7:30 | 150–200 | Por que importa hoje |
| 8 | encerramento | 7:30–8:00 | 60–100 | Síntese + CTA inscrição |

**Total:** 1600–1800 palavras · ~150 WPM · 8 min.

---

### Template 5 min (~1000 palavras)

Para temas simples ou Shorts-to-long teasers.

| Bloco | Tempo | Palavras | Notas |
|-------|-------|----------|-------|
| hook | 0:00–0:20 | 40–60 | 1 frase impacto + 1 pergunta |
| contexto | 0:20–1:00 | 120–150 | Setup mínimo |
| desenvolvimento | 1:00–3:00 | 400–500 | 2 blocos narrativos |
| revelacao | 3:00–4:00 | 150–180 | 1 twist |
| encerramento | 4:00–5:00 | 80–100 | Síntese + CTA |

**Cenas:** 5–6. Sem mid-roll — usar para descoberta ou temas leves.

---

### Template 10 min (~2000 palavras)

Para temas densos com múltiplas camadas.

| Bloco | Tempo | Palavras |
|-------|-------|----------|
| hook | 0:00–0:45 | 60–90 |
| contexto | 0:45–2:00 | 250–300 |
| desenvolvimento_1 | 2:00–4:00 | 300–350 |
| desenvolvimento_2 | 4:00–6:00 | 300–350 |
| revelacao | 6:00–7:30 | 250–300 |
| consequencias | 7:30–8:30 | 200–250 |
| impacto | 8:30–9:30 | 150–200 |
| encerramento | 9:30–10:00 | 80–100 |

**Cenas:** 10–12. Mid-roll em ~8:00. Ideal para RPM alto.

---

### Template 20 min (~4000 palavras)

Para mini-documentários flagship (1x/mês max no pipeline automatizado).

| Bloco | Tempo | Palavras |
|-------|-------|----------|
| hook | 0:00–1:00 | 80–120 |
| contexto | 1:00–3:00 | 400–500 |
| desenvolvimento (4 blocos) | 3:00–14:00 | 2000–2400 |
| revelacao | 14:00–16:00 | 350–400 |
| consequencias | 16:00–18:00 | 300–350 |
| impacto | 18:00–19:00 | 150–200 |
| encerramento | 19:00–20:00 | 100–120 |

**Cenas:** 16–20. Múltiplos mid-rolls. Reservar para outliers com score alto.

---

### Template lista Dark5 (8 min)

Substituir bloco `desenvolvimento` por 5 sub-seções numeradas.

```
hook (30s) → contexto (60s) →
  fato 1 (60s) → fato 2 (60s) → fato 3 (60s) → fato 4 (60s) → fato 5 (60s) →
revelacao (60s) → encerramento (30s)
```

Cada fato = 1 cena visual distinta. Lower third com "FATO 1/5". Thumbnail Layout B.

---

### Hook template (primeiros 15 segundos)

```
[0–3s]  Afirmação chocante ou pergunta impossível de ignorar
        Ex: "Em 1908, algo explodiu com a força de mil bombas atômicas — e não deixou cratera."

[3–8s]  Stakes — por que isso importa
        Ex: "Mais de um século depois, nenhuma teoria consegue explicar completamente o que aconteceu."

[8–15s] Promessa do vídeo
        Ex: "Neste documentário, vamos reconstruir o evento, examinar as três teorias principais — e descobrir por que cientistas ainda evitam falar sobre isso."
```

---

## 4. Tone of voice

| Dimensão | Fazer | Evitar |
|----------|-------|--------|
| Tom | Autoritário, misterioso, factual | Hype, humor, casualidade |
| Pessoa | 3ª pessoa narrativa | 1ª pessoa ("eu acho") |
| Dados | Números, datas, nomes específicos | Generalizações vagas |
| Tensão | Perguntas retóricas, pausas antes de revelações | Spoilers no hook |
| CTA | Sobrio — "inscreva-se para mais documentários" | "CLIQUE AGORA", caps lock |
| TTS | Grave, neutro, ritmo deliberado | Exclamações excessivas |

---

## 5. Checklist de edição (consistência dark)

### Pré-render

- [ ] Roteiro ≥1600 palavras (8 min) ou template correto aplicado
- [ ] Gancho nos primeiros 50–80 palavras
- [ ] 8 cenas com `tipo` mapeado (hook → encerramento)
- [ ] Hero image disponível para thumbnail (cena hook/revelacao/impacto)
- [ ] `thumbnail_texto` ≤4 palavras, UPPERCASE

### Render

- [ ] Intro card 2s com bússola + tema
- [ ] Color grade + vignette aplicados
- [ ] Ken Burns/parallax por tipo de cena (não slideshow estático)
- [ ] Crossfade 0.35–0.6s entre cenas
- [ ] Lower thirds em hook + revelação
- [ ] Watermark 12% opacity
- [ ] Outro card 2.5s com CTA inscrição
- [ ] Legendas SRT sincronizadas

### Pós-render

- [ ] Duração ≥8:00 (mid-roll)
- [ ] Thumbnail Layout A/B/C gerada via BrandKit
- [ ] Preview 168px legível
- [ ] Título ≤70 chars com número/pergunta/consequência
- [ ] Descrição: linha 1 SEO + capítulos 4–6
- [ ] Tags PT + EN
- [ ] Comentário fixado com pergunta

### Adaptáveis (quick wins)

- [ ] Film grain: `noise=alls=5:allf=t` pós-render
- [ ] Gold border 2px no thumbnail
- [ ] Cenas ≤20s (pacing Be Amazed)

---

## 6. Cadência e playlists

| Item | Recomendação |
|------|-------------|
| Frequência | 2–3 vídeos/semana (ter/qui/sáb 18h BRT) |
| Playlists | `Guerras`, `Mistérios`, `Civilizações`, `Ciência` |
| Formato mix | 80% narrativo + 20% lista Dark5 |
| Shorts | Teaser do hook (60s) — fase 2, não core |

---

## 7. Referências cruzadas

| Recurso | Caminho |
|---------|---------|
| Tokens JSON | `design/tokens-dark.json` |
| Copy templates | `templates/copy-templates.md` |
| Análise completa | `docs/dark-channel-analysis.md` |
| BrandKit (código) | `scripts/core/brand_kit.py` |
| Thumbnail generator | `scripts/youtube/thumbnail_generator.py` |
| Prompts IA | `prompts/youtube_*.md` |
| Config plataforma | `scripts/core/platform_config.py` |
