"""
Teste End-to-End da Persona (sem geração automática de imagem)

Usa as imagens colocadas manualmente em
output/mini-aspirador-portátil/assets/images/
e roda o resto do pipeline (roteiro, conteúdo, cenas,
legenda, áudio e renderização) normalmente.

Objetivo: validar que o renderer.py + Ken Burns funcionam
corretamente com as imagens da persona, sem depender da
API de imagem do Gemini (que está bloqueada pelo bug de cota).
"""

from scripts.scoring.product_score import calculate_product_score
from scripts.ai.analysts.ai_analyst import analyze_product
from scripts.affiliate.opportunity_engine import analyze_opportunity
from scripts.decision.decision_engine import decide_action

from scripts.creative.ai_script_generator import generate_ai_script
from scripts.content.content_generator import generate_content
from scripts.video.caption_generator import generate_caption
from scripts.video.scene_generator import generate_scenes
from scripts.video.subtitle_generator import generate_subtitles
from scripts.audio.tts_generator import create_audio

from scripts.video.project_builder import build_video_project
from scripts.video.renderer import render_video_project

from scripts.core.pipeline_result import PipelineResult


def slugify(text):
    return (
        text.lower()
        .replace(" ", "-")
        .replace("/", "-")
    )


produto = {
    "nome": "Mini Aspirador Portátil",
    "categoria": "Casa",
    "visualizacoes": 150000,
    "curtidas": 12000,
    "comentarios": 850,
    "preco_estimado": 79.90
}


print("=" * 40)
print(" TESTE RENDER COM PERSONA (manual)")
print("=" * 40)


print("\n⚠️  Assumindo que as 4 imagens já estão em:")
print(f"    output/{slugify(produto['nome'])}/assets/images/imagem-1.png até imagem-4.png\n")


score = calculate_product_score(produto)
analysis = analyze_product(produto)
opportunity = analyze_opportunity(analysis, score)
action = decide_action(opportunity)

script = generate_ai_script(produto, analysis, opportunity)
content = generate_content(produto, analysis, opportunity, script)
caption = generate_caption(content)
scenes = generate_scenes(produto, content)

subtitles = generate_subtitles({
    "produto": produto,
    "cenas": scenes
})

audio = create_audio({
    "text": content["texto_narracao"],
    "output_path": (
        f"output/{slugify(produto['nome'])}/assets/audio/narracao.mp3"
    )
})


pipeline_result = PipelineResult(
    produto=produto,
    analise=analysis,
    oportunidade=opportunity,
    acao=action,
    roteiro=script,
    conteudo=content,
    legenda=caption,
    cenas=scenes,
    audio=audio,
    subtitle_file=str(subtitles) if subtitles else None
)

result = pipeline_result.to_dict()

build_video_project(result)

video = render_video_project(result)


print("\n" + "=" * 40)
if video:
    print(f"✅ Vídeo final: {video}")
else:
    print("❌ Vídeo não foi gerado — confira se as 4 imagens estão na pasta certa.")
print("=" * 40)