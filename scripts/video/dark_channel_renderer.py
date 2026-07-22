#!/usr/bin/env python3
"""
Dark Channel Renderer — replica o fluxo de canais BR de mistério no YouTube.

Pipeline simples e confiável:
  1. Roteiro dramático (template fixo)
  2. Narração Kokoro TTS (fallback Edge TTS)
  3. Imagens Lorem Picsum (base) + Wikimedia (substituição) + Ken Burns
  4. Legendas queimadas (drawtext)
  5. Música de fundo (6%)
  6. Color grade escuro
  7. Concatenação final
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.video.media_probe import probe_duration

# ---------------------------------------------------------------------------
# STEP 1 — Script template
# ---------------------------------------------------------------------------

SCENE_TEMPLATE: list[dict[str, Any]] = [
    {
        "id": "gancho",
        "narration": (
            "Você está prestes a descobrir algo que poucos sabem sobre {topic}. "
            "O que vou te revelar agora vai mudar completamente a forma como você enxerga esse assunto "
            "para sempre. Prepare-se, porque essa história é perturbadora, profunda e cheia de detalhes "
            "que nunca apareceram nos livros didáticos que você leu na escola. "
            "Durante anos, milhões de pessoas passaram por essa informação sem perceber o que estava "
            "escondido bem diante dos olhos delas. Pesquisadores corajosos arriscaram suas carreiras "
            "para trazer esses fatos à luz, e o que encontraram desafia tudo o que considerávamos "
            "como verdade absoluta. Antes de continuar, peço que fique até o final deste vídeo, "
            "porque a revelação mais chocante vem por último, e ela pode alterar sua percepção "
            "de realidade de um jeito que você jamais imaginou. Respire fundo, ajuste o volume "
            "e preste atenção em cada palavra, porque depois que você souber, não haverá como "
            "desver o que está prestes a ser exposto. Este não é mais um vídeo comum de internet; "
            "é um registro cuidadoso de fatos que resistiram ao tempo e à censura silenciosa "
            "de quem preferia que você nunca chegasse até aqui."
        ),
        "visual_query": "mystery dark documentary cinematic",
        "duration": 60,
    },
    {
        "id": "contexto",
        "narration": (
            "Para entender o mistério de {topic}, precisamos voltar no tempo e reconstruir "
            "cuidadosamente o que realmente aconteceu, longe das versões simplificadas "
            "que nos ensinaram em sala de aula. Durante séculos, esse assunto foi tratado "
            "como um detalhe secundário pelos historiadores oficiais, como se não merecesse "
            "investigação profunda ou debate público honesto. Mas documentos secretos, arquivos "
            "desclassificados e descobertas recentes revelaram uma verdade incômoda que as autoridades "
            "preferem manter escondida do grande público. Registros antigos, cartas trocadas entre "
            "figuras poderosas e relatos de testemunhas ignoradas apontam para uma narrativa "
            "completamente diferente da que conhecemos. A história que nos ensinaram está incompleta, "
            "cuidadosamente editada e, em alguns trechos, deliberadamente distorcida para proteger "
            "interesses que vão muito além do conhecimento científico. Quando você compreende "
            "esse contexto histórico, cada peça do quebra-cabeça começa a se encaixar "
            "de um jeito que ninguém esperava. Museus, arquivos nacionais e bases de dados "
            "acadêmicas guardam indícios que raramente aparecem em documentários mainstream, "
            "mas que, quando reunidos, contam uma história muito mais complexa e inquietante "
            "sobre {topic} do que qualquer narrativa oficial jamais admitiria publicamente."
        ),
        "visual_query": "ancient history documentary cinematic dark",
        "duration": 90,
    },
    {
        "id": "misterio",
        "narration": (
            "O mistério começa quando pesquisadores independentes, cansados de aceitar respostas "
            "prontas, começaram a questionar a versão oficial sobre {topic} com rigor científico "
            "e coragem intelectual. As evidências que encontraram são impossíveis de ignorar, "
            "mesmo para quem tenta desesperadamente mantê-las fora do debate público. "
            "Fotografias de alta resolução, documentos digitalizados, gravações recuperadas "
            "e testemunhos de primeira mão apontam para uma conclusão perturbadora que desafia "
            "o senso comum. Algo fundamental não bate na história que nos contaram durante décadas, "
            "e quanto mais fundo esses investigadores cavaram, mais inconsistências apareceram "
            "como fios soltos de um tecido cuidadosamente costurado para esconder a verdade. "
            "Laboratórios independentes confirmaram anomalias que instituições oficiais se recusaram "
            "a explicar. Mapas antigos, datas conflitantes e registros apagados sugerem "
            "que alguém, em algum momento, decidiu apagar deliberadamente partes essenciais "
            "dessa história. E se essas pistas estiverem corretas, estamos diante de um dos "
            "maiores enigmas já documentados pela humanidade. Cada nova pista reforça "
            "a sensação de que alguém, em algum lugar, trabalhou sistematicamente "
            "para garantir que {topic} permanecesse envolto em mistério, dúvida "
            "e controvérsia por gerações inteiras."
        ),
        "visual_query": "mystery investigation evidence dark cinematic",
        "duration": 90,
    },
    {
        "id": "evidencia",
        "narration": (
            "As evidências sobre {topic} são esmagadoras e continuam se acumulando "
            "mesmo enquanto falamos. Especialistas de universidades renomadas, após analisar "
            "dados brutos sem filtros ideológicos, confirmaram que os números oficiais foram "
            "manipulados ou apresentados de forma seletiva para sustentar uma narrativa "
            "predeterminada. Um estudo publicado em 2019 revelou anomalias inexplicáveis "
            "que nenhum modelo convencional conseguiu justificar de maneira satisfatória. "
            "Relatórios internos, vazamentos de funcionários e perícias independentes "
            "mostram lacunas enormes entre o que foi divulgado à imprensa e o que constava "
            "nos arquivos originais. Os números simplesmente não fecham com a história "
            "que nos foi apresentada durante décadas, e cada nova descoberta reforça "
            "a suspeita de que houve uma campanha coordenada para obscurecer fatos relevantes. "
            "Imagens de satélite, análises geológicas e comparações cronológicas revelam "
            "discrepâncias que não podem ser atribuídas a simples erros de catalogação. "
            "Quando você olha para esse conjunto de provas com honestidade intelectual, "
            "fica claro que algo muito maior está em jogo do que gostaríamos de admitir. "
            "Jornalistas investigativos, arqueólogos independentes e cientistas dissidentes "
            "passaram a usar os mesmos dados brutos e chegaram a conclusões alarmantemente "
            "parecidas sobre {topic}, mesmo trabalhando em países e épocas diferentes."
        ),
        "visual_query": "research documents evidence conspiracy dark",
        "duration": 90,
    },
    {
        "id": "teoria",
        "narration": (
            "A teoria mais aceita entre os pesquisadores que ousaram ir além do consenso "
            "é que {topic} esconde um segredo de proporções colossais, acessível apenas "
            "a um círculo restrito de iniciados que controlam a narrativa pública. "
            "Essa hipótese explica, de forma coerente, todas as inconsistências que encontramos "
            "ao longo desta investigação, conectando pontos que pareciam isolados "
            "em um padrão perturbadoramente lógico. Se essa teoria estiver correta, "
            "tudo o que você acreditava saber sobre esse assunto precisará ser revisado "
            "com humildade e atenção aos detalhes. As implicações são enormes e alcançam "
            "campos que vão da arqueologia à geopolítica, passando por religião, economia "
            "e controle de informação em escala global. Não se trata de especulação vazia, "
            "mas de um modelo explicativo sustentado por evidências convergentes "
            "de fontes independentes. Cada nova descoberta fortalece essa interpretação "
            "e enfraquece as explicações simplistas que durante tanto tempo nos satisfizeram. "
            "Alguns especialistas preferem o silêncio a assumir publicamente posições "
            "que poderiam custar caro às suas reputações. Mas a verdade, quando bem "
            "documentada, tem o incômodo hábito de insistir em ser ouvida. "
            "E quanto mais examinamos {topic} sob essa lente, mais difícil se torna "
            "manter a versão confortável que nos foi vendida como definitiva "
            "por décadas de livros, reportagens e produções televisivas."
        ),
        "visual_query": "theory conspiracy revelation dramatic dark",
        "duration": 90,
    },
    {
        "id": "revelacao",
        "narration": (
            "E aqui está a revelação que pode te deixar sem palavras por alguns instantes. "
            "Depois de anos de investigação silenciosa, cruzamento de fontes e análise "
            "minuciosa de registros esquecidos, a verdade sobre {topic} finalmente veio à tona "
            "de um jeito que não pode mais ser ignorado. O que descobrimos é mais perturbador "
            "do que qualquer teoria da conspiração popular, justamente porque está ancorado "
            "em documentos verificáveis e testemunhos consistentes. Essa informação foi "
            "suprimida por décadas por razões que agora ficam dolorosamente claras "
            "quando observamos quem se beneficiava do silêncio coletivo. Não se trata "
            "de um detalhe menor ou de uma interpretação exagerada de fatos comuns. "
            "Estamos falando de uma reviravolta que reescreve capítulos inteiros "
            "da história humana e obriga a repensar decisões tomadas com base "
            "em premissas falsas. Arquivos recuperados, entrevistas resgatadas "
            "e perícias recentes convergem para a mesma conclusão inescapável. "
            "A partir deste momento, você passa a integrar um grupo reduzido "
            "de pessoas que conhece o que está por trás do véu oficial. "
            "O impacto dessa descoberta sobre {topic} vai muito além do curioso "
            "ou do sensacionalista: ele questiona premissas que sustentam "
            "disciplinas inteiras e exige coragem para ser assimilado "
            "sem filtros ou desculpas intelectuais."
        ),
        "visual_query": "revelation truth dramatic cinematic mystery",
        "duration": 90,
    },
    {
        "id": "conclusao",
        "narration": (
            "Agora você sabe a verdade sobre {topic}, uma verdade que o sistema "
            "não quer que circule livremente entre pessoas curiosas e bem informadas. "
            "O que compartilhamos aqui não é entretenimento superficial, mas um convite "
            "sério para questionar narrativas prontas e buscar fontes primárias "
            "com espírito crítico. Compartilhe esse vídeo com quem você confia, "
            "porque esse tipo de conteúdo costuma ser removido ou limitado "
            "assim que começa a alcançar um público maior. Cada visualização, "
            "cada comentário e cada inscrição fortalece um espaço independente "
            "onde ideias incômodas ainda podem ser discutidas com honestidade. "
            "Se você quer continuar descobrindo segredos como esse, se inscreva no canal, "
            "ative o sininho e fique atento aos próximos episódios. A jornada "
            "pelo desconhecido não termina aqui. Na verdade, ela está apenas começando, "
            "e as próximas revelações prometem ser ainda mais surpreendentes "
            "do que tudo o que você acabou de ouvir. Guarde o que aprendeu "
            "sobre {topic}, questione o que te contaram e nunca aceite "
            "verdades prontas sem examinar as evidências por conta própria."
        ),
        "visual_query": "truth revelation subscribe channel dark",
        "duration": 60,
    },
]

WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"
GRADIENT_FILTER = "gradients=s=1920x1080:c0=0x0a0a1a:c1=0x1a1a3e"
COLOR_GRADE = "curves=vintage,eq=contrast=1.2:brightness=-0.05:saturation=0.8,hue=h=200:s=0.3"
KEN_BURNS_ZOOM = "scale=8000:-1,zoompan=z='min(zoom+0.0015,1.5)':d='{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)',scale=1920:1080,fps=25"
TTS_VOICE = "pt-BR-FranciscaNeural"
TTS_RATE = "-10%"
TTS_PITCH = "-5Hz"
MUSIC_VOLUME = 0.06
AUDIO_LIBRARY = ROOT / "assets" / "audio" / "library.json"
DARK_AMBIENT_PATH = ROOT / "assets" / "audio" / "dark_ambient.mp3"
DARK_MOODS = {"melancholic", "tense", "investigative", "mystery", "dark ambient", "dark_ambient"}


def build_script(topic: str) -> list[dict[str, Any]]:
    """STEP 1 — Gera cenas a partir do template dramático."""
    scenes = []
    for item in SCENE_TEMPLATE:
        scenes.append(
            {
                "id": item["id"],
                "narration": item["narration"].format(topic=topic),
                "visual_query": item["visual_query"],
                "duration": item["duration"],
            }
        )
    return scenes


def full_narration_text(scenes: list[dict[str, Any]]) -> str:
    return " ".join(scene["narration"] for scene in scenes)


# ---------------------------------------------------------------------------
# STEP 2 — Narration (Kokoro TTS, Edge TTS fallback)
# ---------------------------------------------------------------------------


async def _synthesize_narration_edge(text: str, output_path: Path) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(
        text,
        TTS_VOICE,
        rate=TTS_RATE,
        pitch=TTS_PITCH,
    )
    await communicate.save(str(output_path))


def _convert_wav_to_mp3(wav_path: Path, mp3_path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(wav_path),
            "-c:a", "libmp3lame",
            "-q:a", "2",
            str(mp3_path),
        ],
        check=True,
        capture_output=True,
    )


def generate_narration(scenes: list[dict[str, Any]], output_dir: Path) -> tuple[Path, float]:
    """STEP 2 — Narração PT-BR com pausas dramáticas via Kokoro TTS (Edge fallback)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    narration_path = output_dir / "narration.mp3"
    text = full_narration_text(scenes)

    voice = os.environ.get("KOKORO_VOICE", "pf_dora")
    speed = float(os.environ.get("KOKORO_SPEED", "0.85"))

    try:
        from scripts.audio.kokoro_tts import generate_narration_kokoro

        wav_path = output_dir / "narration.wav"
        print(f"[STEP 2] Gerando narração Kokoro TTS (voice={voice}, speed={speed})...")
        generate_narration_kokoro(text, str(wav_path), voice=voice, speed=speed)
        _convert_wav_to_mp3(wav_path, narration_path)
    except Exception:
        asyncio.run(_synthesize_narration_edge(text, narration_path))

    duration = probe_duration(narration_path)
    if duration <= 0:
        raise RuntimeError(f"Falha ao obter duração de {narration_path}")

    print(f"[STEP 2] Narração salva: {narration_path} ({duration:.1f}s)")
    return narration_path, duration


# ---------------------------------------------------------------------------
# STEP 3 — Footage (Wikimedia + Ken Burns)
# ---------------------------------------------------------------------------


WIKIMEDIA_HEADERS = {
    "User-Agent": "AI-Commerce-OS/1.0 (dark-channel-renderer; contact: projeto-atlas@example.com)",
    "Accept": "application/json",
}


def _wikimedia_search_jpg(query: str) -> str | None:
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srnamespace": "6",
        "srlimit": "10",
        "format": "json",
    }
    response = requests.get(
        WIKIMEDIA_API, params=params, timeout=15, headers=WIKIMEDIA_HEADERS,
    )
    response.raise_for_status()
    hits = response.json().get("query", {}).get("search", [])

    for hit in hits:
        title = hit.get("title", "")
        if not title.lower().endswith(".jpg"):
            continue
        title_encoded = title.replace(" ", "_")
        info = requests.get(
            WIKIMEDIA_API,
            params={
                "action": "query",
                "titles": title_encoded,
                "prop": "imageinfo",
                "iiprop": "url",
                "format": "json",
            },
            timeout=15,
            headers=WIKIMEDIA_HEADERS,
        )
        info.raise_for_status()
        pages = info.json().get("query", {}).get("pages", {})
        for page in pages.values():
            imageinfo = page.get("imageinfo", [])
            if imageinfo:
                return imageinfo[0].get("url")
    return None


def _download_image_from_url(
    url: str,
    dest: Path,
    *,
    headers: dict[str, str] | None = None,
) -> bool:
    try:
        data = requests.get(url, timeout=30, headers=headers or {}).content
        if not data:
            return False
        dest.write_bytes(data)
        return True
    except Exception as exc:
        print(f"[STEP 3] Download falhou ({url!r}): {exc}")
        return False


def _try_wikimedia_replacement(query: str, dest: Path) -> bool:
    """Tenta substituir a imagem base por uma foto real do Wikimedia."""
    for attempt in range(1, 3):
        try:
            url = _wikimedia_search_jpg(query)
            if not url:
                raise ValueError(f"Nenhuma .jpg encontrada para {query!r}")
            if _download_image_from_url(url, dest, headers=WIKIMEDIA_HEADERS):
                print(f"[STEP 3] Wikimedia substituiu imagem base: {query!r}")
                return True
        except Exception as exc:
            print(f"[STEP 3] Wikimedia tentativa {attempt}/2 falhou ({query!r}): {exc}")
            if attempt < 2:
                time.sleep(2)

    words = query.strip().split()
    if len(words) > 2:
        short_query = " ".join(words[:2])
        print(f"[STEP 3] Tentando query simplificada: {short_query!r}")
        try:
            url = _wikimedia_search_jpg(short_query)
            if url and _download_image_from_url(url, dest, headers=WIKIMEDIA_HEADERS):
                print(f"[STEP 3] Wikimedia substituiu imagem base: {short_query!r}")
                return True
        except Exception as exc:
            print(f"[STEP 3] Query simplificada falhou ({short_query!r}): {exc}")

    return False


def download_scene_image(query: str, dest: Path, scene_index: int = 0, *, topic: str = "") -> bool:
    """Baixa Picsum como base garantida, depois tenta Wikimedia como substituição."""
    picsum_url = f"https://picsum.photos/1920/1080?random={scene_index}&blur=0"
    print(f"[STEP 3] Baixando imagem base (Picsum): {picsum_url}")
    if not _download_image_from_url(picsum_url, dest):
        return False

    # Query enriquecida com o nome do tópico para Wikimedia achar imagens relevantes
    wikimedia_query = f"{topic} {query}" if topic else query
    _try_wikimedia_replacement(wikimedia_query, dest)
    return True


def create_gradient_image(dest: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", GRADIENT_FILTER, "-frames:v", "1", str(dest)],
        check=True,
        capture_output=True,
    )


def create_ken_burns_clip(image_path: Path, output_path: Path, duration: float) -> None:
    frames = int(duration * 25)
    print(f"[STEP 3] Ken Burns ffmpeg: duration={duration}s, frames={frames}")
    vf = KEN_BURNS_ZOOM.format(frames=frames)
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(image_path),
            "-vf", vf,
            "-t", str(duration),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            str(output_path),
        ],
        check=True,
        capture_output=True,
    )


def fetch_footage_for_scenes(scenes: list[dict[str, Any]], work_dir: Path, *, topic: str = "") -> list[Path]:
    """STEP 3 — Picsum (base) + Wikimedia (opcional) + Ken Burns por cena."""
    images_dir = work_dir / "images"
    raw_dir = work_dir / "raw_clips"
    images_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    raw_clips: list[Path] = []
    for index, scene in enumerate(scenes):
        scene_id = scene["id"]
        duration = float(scene["duration"])
        image_path = images_dir / f"scene_{index}_base.jpg"
        raw_path = raw_dir / f"{index:02d}_{scene_id}.mp4"

        print(f"[STEP 3] Cena {scene_id}: duration={duration}s, query={scene['visual_query']!r}")
        if not download_scene_image(scene["visual_query"], image_path, scene_index=index, topic=topic):
            print(f"[STEP 3] Cena {scene_id}: Picsum falhou — usando gradiente escuro")
            create_gradient_image(image_path)

        create_ken_burns_clip(image_path, raw_path, duration)
        actual_duration = probe_duration(raw_path)
        print(f"Scene {index} clip: {actual_duration:.1f}s (expected {duration:.0f}s)")
        raw_clips.append(raw_path)
        print(f"[STEP 3] Cena {scene_id}: {raw_path.name}")

    return raw_clips


# ---------------------------------------------------------------------------
# STEP 4 — Burn-in subtitles
# ---------------------------------------------------------------------------


def _resolve_bold_font() -> str:
    candidates = [
        "/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf",
        "/usr/share/fonts/truetype/msttcorefonts/arialbd.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        str(ROOT / "assets" / "brand" / "fonts" / "Roboto-Bold.ttf"),
    ]
    for path in candidates:
        if Path(path).is_file():
            return path
    return ""


def _escape_drawtext(text: str) -> str:
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace("'", "\\'")
    text = text.replace("%", "\\%")
    return text


def split_subtitle_chunks(text: str, max_words: int = 5) -> list[str]:
    words = re.findall(r"\S+", text)
    chunks: list[str] = []
    for i in range(0, len(words), max_words):
        chunks.append(" ".join(words[i : i + max_words]))
    return chunks


def build_subtitle_timings(
    text: str,
    total_duration: float,
    max_words: int = 5,
) -> list[tuple[str, float, float]]:
    words = re.findall(r"\S+", text)
    if not words:
        return []

    chunks = split_subtitle_chunks(text, max_words=max_words)
    timings: list[tuple[str, float, float]] = []
    word_index = 0

    for chunk in chunks:
        chunk_words = len(re.findall(r"\S+", chunk))
        start = (word_index / len(words)) * total_duration
        end = ((word_index + chunk_words) / len(words)) * total_duration
        timings.append((chunk, start, end))
        word_index += chunk_words

    return timings


def _drawtext_filters_for_scene(
    timings: list[tuple[str, float, float]],
    scene_start: float,
    scene_end: float,
    font_path: str,
) -> str:
    filters: list[str] = []
    font_opt = f":fontfile={font_path}" if font_path else ":font=Arial Bold"

    for text, global_start, global_end in timings:
        if global_end <= scene_start or global_start >= scene_end:
            continue
        local_start = max(0.0, global_start - scene_start)
        local_end = min(scene_end - scene_start, global_end - scene_start)
        escaped = _escape_drawtext(text)
        filters.append(
            f"drawtext=text='{escaped}'{font_opt}"
            f":fontsize=52:fontcolor=white:borderw=4:bordercolor=black"
            f":box=1:boxcolor=black@0.35:boxborderw=10"
            f":x=(w-text_w)/2:y=h-140"
            f":enable='between(t\\,{local_start:.3f}\\,{local_end:.3f})'"
        )
    return ",".join(filters)


def scene_time_offsets(scenes: list[dict[str, Any]]) -> list[tuple[float, float]]:
    offsets: list[tuple[float, float]] = []
    cursor = 0.0
    for scene in scenes:
        duration = float(scene["duration"])
        offsets.append((cursor, cursor + duration))
        cursor += duration
    return offsets


def apply_grade_and_subtitles(
    input_clip: Path,
    output_clip: Path,
    subtitle_filter: str,
) -> None:
    vf_parts = [COLOR_GRADE]
    if subtitle_filter:
        vf_parts.append(subtitle_filter)
    vf = ",".join(vf_parts)

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(input_clip),
            "-vf", vf,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-an",
            str(output_clip),
        ],
        check=True,
        capture_output=True,
    )


def burn_subtitles_on_scenes(
    scenes: list[dict[str, Any]],
    raw_clips: list[Path],
    narration_text: str,
    narration_duration: float,
    work_dir: Path,
) -> list[Path]:
    """STEP 4 + STEP 6 — Legendas queimadas e color grade por cena."""
    graded_dir = work_dir / "graded_clips"
    graded_dir.mkdir(parents=True, exist_ok=True)

    font_path = _resolve_bold_font()
    timings = build_subtitle_timings(narration_text, narration_duration)
    offsets = scene_time_offsets(scenes)
    graded_clips: list[Path] = []

    for index, (raw_clip, (start, end)) in enumerate(zip(raw_clips, offsets)):
        scene_id = scenes[index]["id"]
        subtitle_filter = _drawtext_filters_for_scene(timings, start, end, font_path)
        out_path = graded_dir / f"{index:02d}_{scene_id}_final.mp4"
        print(f"[STEP 4/6] Cena {scene_id}: legendas + color grade")
        apply_grade_and_subtitles(raw_clip, out_path, subtitle_filter)
        graded_clips.append(out_path)

    return graded_clips


# ---------------------------------------------------------------------------
# STEP 5 — Background music
# ---------------------------------------------------------------------------


def pick_dark_ambient_track() -> Path | None:
    if DARK_AMBIENT_PATH.is_file():
        return DARK_AMBIENT_PATH

    if not AUDIO_LIBRARY.is_file():
        return None

    try:
        library = json.loads(AUDIO_LIBRARY.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    tracks = library.get("tracks", [])
    if not tracks:
        return None

    audio_root = AUDIO_LIBRARY.parent

    def _score(track: dict) -> int:
        mood = str(track.get("mood", "")).lower()
        track_id = str(track.get("id", "")).lower()
        if mood in DARK_MOODS or "mystery" in mood or "dark" in mood:
            return 0
        if "mystery" in track_id or "dark" in track_id:
            return 1
        if mood in {"reveal"}:
            return 2
        return 3

    ready = [t for t in tracks if t.get("ready", True)]
    if not ready:
        return None

    ready.sort(key=_score)
    for track in ready:
        rel = track.get("file", "")
        path = audio_root / rel
        if path.is_file():
            return path
    return None


def mix_background_music(narration_path: Path, output_path: Path, duration: float) -> Path:
    """STEP 5 — Mixa música dark ambient a 6% sobre a narração."""
    music_path = pick_dark_ambient_track()
    if not music_path:
        print("[STEP 5] Sem música disponível — pulando")
        return narration_path

    print(f"[STEP 5] Mixando {music_path.name} a {int(MUSIC_VOLUME * 100)}%")
    filter_complex = (
        f"[1:a]aloop=loop=-1:size=2e+09,atrim=0:{duration:.3f},"
        f"volume={MUSIC_VOLUME}[music];"
        f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=0[aout]"
    )
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(narration_path),
            "-i", str(music_path),
            "-filter_complex", filter_complex,
            "-map", "[aout]",
            "-c:a", "libmp3lame",
            "-q:a", "2",
            str(output_path),
        ],
        check=True,
        capture_output=True,
    )
    return output_path


# ---------------------------------------------------------------------------
# STEP 7 — Final render
# ---------------------------------------------------------------------------


def concatenate_final_video(
    scene_clips: list[Path],
    audio_path: Path,
    output_path: Path,
) -> Path:
    """STEP 7 — Concatena cenas (corte seco) + áudio final."""
    work_dir = output_path.parent
    concat_list = work_dir / "concat_list.txt"
    lines = [f"file '{clip.resolve()}'" for clip in scene_clips]
    concat_list.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("[STEP 7] Render final (concat + áudio)...")
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-i", str(audio_path),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-shortest",
            str(output_path),
        ],
        check=True,
        capture_output=True,
    )
    return output_path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_dark_channel_video(
    topic: str,
    output_dir: str | Path,
    *,
    output_filename: str = "video_final.mp4",
) -> Path:
    """
    Executa os 7 passos e retorna o caminho do vídeo final.
    """
    output_dir = Path(output_dir)
    work_dir = output_dir / "dark_channel_work"
    work_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🌑 Dark Channel Renderer — {topic}\n")

    # STEP 1
    scenes = build_script(topic)
    print(f"[STEP 1] Roteiro: {len(scenes)} cenas")

    # STEP 2
    narration_path, narration_duration = generate_narration(scenes, output_dir)
    narration_text = full_narration_text(scenes)

    # STEP 3
    raw_clips = fetch_footage_for_scenes(scenes, work_dir, topic=topic)

    # STEP 4 + 6
    graded_clips = burn_subtitles_on_scenes(
        scenes,
        raw_clips,
        narration_text,
        narration_duration,
        work_dir,
    )

    # STEP 5
    mixed_audio_path = output_dir / "narration_mixed.mp3"
    final_audio = mix_background_music(narration_path, mixed_audio_path, narration_duration)

    # STEP 7
    final_video = output_dir / output_filename
    concatenate_final_video(graded_clips, final_audio, final_video)

    print(f"\n✅ Vídeo dark channel: {final_video}\n")
    return final_video


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Dark Channel Renderer")
    parser.add_argument("topic", help="Tema do vídeo")
    parser.add_argument(
        "-o", "--output-dir",
        default="output/dark_channel",
        help="Diretório de saída",
    )
    parser.add_argument(
        "--output-filename",
        default="video_final.mp4",
        help="Nome do arquivo de vídeo final",
    )
    args = parser.parse_args()

    try:
        render_dark_channel_video(
            args.topic,
            args.output_dir,
            output_filename=args.output_filename,
        )
        return 0
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode() if exc.stderr else str(exc)
        print(f"❌ ffmpeg falhou: {stderr}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"❌ Erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
