# Touch Portal — AI-Commerce-OS

Pacote de **icones**, **page** e **plugin** para o Touch Portal.

## Problema que resolve

Pages importadas da comunidade costumam vir **sem icones e sem nomes** porque faltam os PNGs referenciados. Este pacote inclui tudo embutido.

## Instalacao rapida (Windows)

1. **Feche** o Touch Portal (bandeja → Exit)
2. No PowerShell, na raiz do projeto:

```powershell
git fetch origin cursor/touchportal-icons-c0f0
git checkout origin/cursor/touchportal-icons-c0f0 -- touchportal
python touchportal\build\build_assets.py
powershell -ExecutionPolicy Bypass -File .\touchportal\install.ps1 -AsMainPage
```

3. Abra o Touch Portal → se pedir, clique **Trust Always** no plugin

### Se faltarem icones (so 4 de 8)

```powershell
powershell -ExecutionPolicy Bypass -File .\touchportal\repair-icons.ps1
Copy-Item touchportal\pages\aicommerce-main.tml "$env:APPDATA\TouchPortal\pages\(main).tml" -Force
```

Feche e reabra o Touch Portal.

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
