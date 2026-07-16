"""Testes para Subtitle Engine."""



import unittest



from scripts.video.subtitle_engine import (

    _chunk_by_words,

    _split_into_lines,

    generate_scene_subtitles,

    validate_srt_timing,

)





class TestSubtitleEngine(unittest.TestCase):



    def test_split_max_two_lines(self):

        text = "Esta é uma frase longa que precisa ser dividida em linhas menores para legenda"

        result = _split_into_lines(text, max_chars=38, max_lines=2)

        lines = result.split("\n")

        self.assertLessEqual(len(lines), 2)



    def test_chunk_by_words(self):

        text = "Primeira frase curta. Segunda frase com mais palavras aqui. Terceira frase final."

        chunks = _chunk_by_words(text, max_words=5)

        self.assertGreater(len(chunks), 1)

        for chunk in chunks:

            self.assertLessEqual(len(chunk), 80)



    def test_generate_scene_subtitles(self):

        scenes = [{

            "tempo_inicio": 0.0,

            "tempo_fim": 10.0,

            "narracao": "Em 1908 algo explodiu na Sibéria com força devastadora.",

        }]

        srt, ass = generate_scene_subtitles(scenes)

        self.assertIn("00:00:00", srt)

        self.assertIn("Dialogue:", ass)
        self.assertIn(",44,", ass)



    def test_timing_offset_applied(self):

        scenes = [{

            "tempo_inicio": 0.0,

            "tempo_fim": 5.0,

            "narracao": "Texto curto de teste.",

        }]

        srt, _ = generate_scene_subtitles(scenes, timing_offset=2.0)

        self.assertIn("00:00:02", srt)



    def test_validate_srt_matches_audio(self):

        scenes = [{

            "tempo_inicio": 0.0,

            "tempo_fim": 12.0,

            "narracao": "Primeira frase. Segunda frase com mais conteúdo aqui.",

        }]

        srt, _ = generate_scene_subtitles(

            scenes,

            timing_offset=2.0,

            audio_duration=12.0,

        )

        ok, reason = validate_srt_timing(srt, 12.0, timing_offset=2.0)

        self.assertTrue(ok, reason)





if __name__ == "__main__":

    unittest.main()

