# Deploy na Nuvem — Guia para o Dono

> **Hetzner foi abandonado** (exige SSH). Use **Railway.app** — zero SSH, deploy pelo GitHub.

**Guia completo:** [docs/deploy-railway.md](deploy-railway.md)

---

## Resumo em 5 passos

1. **Criar conta** em [railway.app](https://railway.app) e conectar o repositório GitHub.
2. **Configurar** 4 GB RAM + variáveis (`PIPELINE_API_KEY`, `GEMINI_API_KEY`, `PEXELS_API_KEY`) no painel Railway.
3. **Copiar** a URL pública do Railway e a chave API para o `.env` do PC (ou rode `.\scripts\cloud\configurar_pc.ps1`).
4. **Testar:** `python scripts/cloud/gerar_video.py --topic "teste de conexão"`
5. **Gerar vídeo:** `.\scripts\cloud\gerar_video.ps1 -Topic "Seu tema aqui"`

---

## Por que Railway?

| Opção | Custo | SSH? | Jobs longos (FFmpeg)? |
|-------|-------|------|----------------------|
| **Railway** ✅ | ~R$ 25/mês | Não | Sim |
| Render | R$ 40+ | Não | Timeout |
| Cloud Run | centavos | Não | Setup complexo |
| Modal | variável | Não | Reescrever código |
| Replicate | por uso | Não | Só modelos IA |
| ~~Hetzner~~ | R$ 22 | **Sim** ❌ | Sim |

---

## Comando do dia a dia

```powershell
.\scripts\cloud\gerar_video.ps1 -Topic "A verdade sobre a Biblioteca de Alexandria"
```

O MP4 aparece em `downloads/` quando pronto. Seu PC não processa nada pesado.
