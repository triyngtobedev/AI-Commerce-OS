# Touch Portal — AI-Commerce-OS

Pacote de **icones**, **page** e **plugin** para o Touch Portal.

## Problema que resolve

Pages importadas da comunidade costumam vir **sem icones e sem nomes** porque faltam os PNGs referenciados. Este pacote inclui tudo embutido.

## Corrigir botoes sem icone (Windows)

**Nao recria botoes** — apenas copia os PNGs e atualiza o campo de imagem nos botoes existentes.

1. **Feche** o Touch Portal (bandeja do sistema -> Exit)
2. No PowerShell:

```powershell
cd C:\Projetos\AI-Commerce-OS
git pull
powershell -ExecutionPolicy Bypass -File .\touchportal\repair-icons.ps1
```

Ou clique duplo em `touchportal\repair-icons.bat`.

3. Abra o Touch Portal de novo — os 8 icones devem aparecer no celular.

### O que o script faz

| Passo | Acao |
|-------|------|
| 1 | Copia 8 PNGs para `%APPDATA%\TouchPortal\icons\` |
| 2 | Atualiza `(main).tml` in-place (preserva IDs e acoes) |
| 3 | Verifica que cada botao referencia um PNG existente |

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
