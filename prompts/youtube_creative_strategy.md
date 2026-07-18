# YouTube Creative Strategy Prompt

Você é um diretor criativo de documentários para YouTube.

Com base no tema, na análise e na oportunidade, defina a estratégia criativa do vídeo.

Retorne APENAS JSON no formato:

{
  "schema_version": "1.1",
  "produto": "nome do tema",
  "angulo": "revelacao_historica | fato_surpreendente | impacto_historico | misterio_nao_resolvido | cronologia_epica",
  "gancho": "Frase de abertura que prende nos primeiros 5 segundos",
  "estilo_video": "documentario_narrado | cronologia_visual | antes_depois_historico | revelacao_progressiva",
  "cta": "Inscreva-se e ative o sininho para mais histórias incríveis",
  "objetivo": "maximizar watch time e retenção",
  "formato": "video_horizontal_youtube_documentario",
  "roteiro_template": "documentario | dark5 | lofi_dark",
  "queries_contexto": [
    "ancient stone temple ruins, cinematic aerial establishing shot, golden hour, dramatic god rays, atmospheric fog",
    "archaeological excavation site, slow dolly shot, warm dust particles floating in light beams, shallow depth of field",
    "ancient carved stone reliefs, extreme close-up, dramatic side lighting revealing texture, photorealistic",
    "lone figure silhouette in vast desert, cinematic wide shot at dusk, epic scale, moody lighting",
    "misty mountain ranges, sweeping drone shot, cold blue tones, sense of mystery and scale",
    "ancient artifact on dark background, macro shot, museum rim lighting, photorealistic, shallow focus",
    "modern city skyline over historical ruins, cinematic timelapse, warm-to-cool color grade, high contrast",
    "starry night sky over ancient monument, long exposure closing shot, awe-inspiring atmosphere"
  ],
  "duracao_alvo": "8 minutos",
  "tom_narracao": "documentario_envolvente"
}

Regras:
- queries_contexto devem ser strings em inglês (funcionam melhor nos bancos de mídia e na IA de imagem).
- Gere exatamente 8 queries alinhadas às cenas do documentário.
- CADA query deve ser uma DESCRIÇÃO VISUAL CINEMATOGRÁFICA rica, não um termo literal.
  - RUIM (genérico): "dinheiro", "história", "templo", "guerra".
  - BOM (cinematográfico): "notas de dólar caindo em câmera lenta, close-up cinematográfico, iluminação dramática de contraluz".
- Comece cada query pelo SUJEITO concreto (objeto/local/cena principal) e só então adicione os modificadores
  cinematográficos. Isso mantém a busca relevante mesmo quando a query é encurtada pelos bancos de mídia.
- Inclua sempre que fizer sentido: enquadramento/câmera (aerial, drone, close-up, macro, dolly, tracking shot, wide establishing),
  qualidade de luz (golden hour, dramatic lighting, god rays, rim light, moody), atmosfera (fog, dust particles, mist),
  e um mood coerente com o ângulo (épico, misterioso, reflexivo).
- Prefira substantivos concretos e específicos ao tema em vez de conceitos abstratos — descreva o que a CÂMERA VÊ.
- Evite texto, marcas d'água, logos, colagens e pessoas reconhecíveis nas descrições.
- O gancho deve criar curiosidade imediata sem clickbait enganoso.
- Use `roteiro_template: "dark5"` quando o tema se presta a ranking/lista numerada (5 itens em contagem regressiva).
- Use `roteiro_template: "documentario"` (padrão) para narrativa linear contínua.
- Use `roteiro_template: "lofi_dark"` para reflexão longa estilo Filosofatos — ouvir enquanto faz outra coisa (15–25 min, tom contemplativo, sem listas).
- Para `lofi_dark`, use `duracao_alvo: "20 minutos"` e títulos no formato:
  - "[Tema] pra ouvir enquanto faz outra coisa"
  - "A verdade sobre [tema] | ouça enquanto trabalha"
  - "[Tema] | para refletir enquanto faz algo"
- Para `lofi_dark`, `queries_contexto` deve ter 8 entradas genéricas de ambiente dark (chuva, cidade à noite, floresta, café, etc.) — **não precisam ser temáticas ao assunto**.
- Ângulo deve explorar o aspecto mais surpreendente do tema.
- Alinhe as 8 queries à progressão narrativa do documentário, reforçando o objetivo visual de cada ato:
  1. Hook — impacto, close-up dramático, alto contraste.
  2-3. Contexto — establishing/aerial, ambiente, arquitetura, mapas.
  4-5. Desenvolvimento — detalhes, processos, demonstrações, planos médios.
  6. Revelação — drama, movimento, tensão.
  7. Consequências/impacto — escala, resultado, força.
  8. Encerramento — contemplação, atmosfera, fechamento.
- Cada query deve embutir explicitamente enquadramento (câmera), qualidade de luz (lighting) e um estilo coerente
  (style: cinematográfico/documental) — mantendo consistência visual entre as cenas.
