# Resultados dos Testes de APIs de Vídeo

> Gerado em: 2026-07-18 00:10:37

## Status

✅ Primeiro vídeo real gerado com sucesso via CLI.

## Configuração detectada

| API | Configurada |
|-----|-------------|
| Kling Web (grátis) | ✅ |
| fal.ai Kling 2.6 Pro | ❌ |
| Replicate Wan 2.6 | ✅ |
| fal.ai Wan (HF Router) | ✅ |

## Resultado do teste real (CLI)

| Métrica | Valor |
|---------|-------|
| API usada | `replicate` |
| Tempo total (s) | 146.68 |
| Resolução | 1280x720 |
| Duração vídeo (s) | 5.0 |
| Tamanho (bytes) | 3952489 |
| Créditos restantes | None |
| Fallback | kling_web falhou (Créditos Kling web esgotados) → tentando replicate |
| Arquivo | `output\videos\teste_kling.mp4` |

## Comando executado

```bash
python -m src.video_generator \
  --prompt "sneaker product shot, studio lighting, slow zoom" \
  --output ./output/videos/test_real.mp4
```

## Vídeos gerados

- **test_real**: ✅ `output\videos\teste_kling.mp4`

## Observações

1. Kling Web (66 créditos/dia) → fal.ai Kling 2.6 Pro → Replicate Wan 2.6 → HF Wan2.2.
2. Configure FAL_KEY (fal.ai), REPLICATE_API_TOKEN e KLING_EMAIL/PASSWORD.
3. Testes unitários: `pytest tests/test_video_apis.py -v -m "not integration"`.
