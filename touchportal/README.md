# Touch Portal — AI-Commerce-OS

Configuração **automática** de botões, ícones e navegação entre pages ACOS.

## Instalação em 1 comando (Windows)

1. **Feche** o Touch Portal (bandeja → Exit)
2. No PowerShell:

```powershell
cd C:\Projetos\AI-Commerce-OS
git pull
powershell -ExecutionPolicy Bypass -File .\touchportal\configure-all.ps1
```

Ou clique duplo em `touchportal\configure-all.bat`.

3. Abra o Touch Portal → Settings → Plug-ins → **Trust Always** no AI-Commerce-OS
4. Settings → Backups → criar backup

## O que o script faz (sem UI manual)

| Passo | Ação |
|-------|------|
| 1 | Backup das `.tml` atuais |
| 2 | Copia 8 ícones PNG para `%APPDATA%\TouchPortal\icons\` |
| 3 | Instala plugin estático (sem `plugin_start_cmd` — não reescreve pages) |
| 4 | Gera e implanta 6 pages com botões, ícones e navegação |
| 5 | Copia `.tpz` para Desktop (import opcional) |
| 6 | Verifica `(main).tml` sem BOM e conta botões |

## Pages configuradas

| Page | Conteúdo |
|------|----------|
| **(main)** | 8 botões com ícones: Cursor, VS Code, Projeto, Pipeline, Docker, Git Push, Terminal, Railway |
| **ACOS Home** | Apps + navegação → Produção, Nuvem, Git |
| **ACOS Produção** | Pipeline IA, Último vídeo, Outputs, Git, Docker, Terminal |
| **ACOS Pipeline** | IA, Rerun, Local, Logs, API |
| **ACOS Git** | Commit, Push, Status |
| **ACOS Nuvem** | Railway, YT Studio, Reiniciar API, Limpar cache |

Navegação entre pages usa **Go To Page** (Navigation).

## Touch Portal gratuito

- **PC:** todas as 6 pages funcionam
- **Celular:** máximo **2 pages** ((main) + 1). Use (main) como hub principal

## Reparar só ícones (pages já existentes)

```powershell
powershell -ExecutionPolicy Bypass -File .\touchportal\repair-icons.ps1
```

## Proteção contra corrupção

- Pages são escritas via **Python** (`json.dumps`), nunca via `ConvertTo-Json` do PowerShell
- Plugin **não** tem serviço em background (`plugin_start_cmd` ausente)
- Backup automático antes de cada deploy
- `(main).tml` validado sem UTF-8 BOM

## Caminho do projeto

Edite `%APPDATA%\TouchPortal\plugins\AI-Commerce-OS\config.json`:

```json
{ "projectRoot": "C:\\Projetos\\AI-Commerce-OS" }
```

Ou passe na instalação:

```powershell
.\touchportal\configure-all.ps1 -ProjectRoot "D:\MeusProjetos\AI-Commerce-OS"
```

## Desenvolvimento

Regenerar pacotes:

```bash
python touchportal/build/build_pack.py
python touchportal/build/build_assets.py   # page simples 2x4 (legado)
```
