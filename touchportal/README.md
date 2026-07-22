# Touch Portal — AI-Commerce-OS

Pacote de **icones**, **page** e **plugin** para o Touch Portal.

## Problema que resolve

Pages importadas da comunidade costumam vir **sem icones e sem nomes** porque faltam os PNGs referenciados. Este pacote inclui tudo embutido.

## Instalacao rapida (Windows)

**Nao precisa rodar `build_assets.py`** - os icones ja vem prontos em `source/icons/`.

1. **Feche** o Touch Portal (bandeja -> Exit)
2. No PowerShell:

```powershell
cd C:\Projetos\AI-Commerce-OS
git fetch origin cursor/touchportal-icons-c0f0
git checkout origin/cursor/touchportal-icons-c0f0 -- touchportal
powershell -ExecutionPolicy Bypass -File .\touchportal\repair-icons.ps1
```

3. Abra o Touch Portal de novo

### Se faltarem icones

```powershell
powershell -ExecutionPolicy Bypass -File .\touchportal\repair-icons.ps1
```

## Instalacao via import (alternativa)

Depois de rodar `build_assets.py`, importe manualmente no Touch Portal:

| Arquivo | Menu |
|---------|------|
| `dist/AI-Commerce-OS.tpp` | Settings → Import plug-in |
| `dist/AI-Commerce-OS-Icons.tpi` | Wrench → Import iconpack |
| `dist/AI-Commerce-OS-Main.tpz` | Pages → Import Page |

## Layout dos botoes (2×4)

| Cursor | VS Code | Projeto | Pipeline IA |
| Docker | Git Push | Terminal | Railway |

Icones coloridos em tela cheia, no estilo da page de referencia.

## Configurar caminho do projeto

Edite `%APPDATA%\TouchPortal\plugins\AI-Commerce-OS\config.json`:

```json
{
  "projectRoot": "C:\\Projetos\\AI-Commerce-OS"
}
```

Ou passe na instalacao:

```powershell
.\touchportal\install.ps1 -ProjectRoot "D:\MeusProjetos\AI-Commerce-OS"
```
