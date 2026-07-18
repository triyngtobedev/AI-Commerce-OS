# Scripts de desenvolvimento — NÃO usar em produção

Esta pasta contém utilitários para **desenvolvedores/agentes** debugarem o pipeline
**localmente**. O dono do projeto **nunca** deve rodar estes comandos.

## Comando oficial (PC do dono)

Todo processamento pesado roda no **Railway**. No PC, use apenas:

```bash
python scripts/cloud/gerar_video.py --topic "Seu tema" --template lofi_dark
```

## Scripts desta pasta (dev only)

| Script | Uso |
|--------|-----|
| `gerar_lofi_dark.py` | Executa pipeline lofi_dark **localmente** — só para debug |
