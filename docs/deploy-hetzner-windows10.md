# Deploy na Hetzner — Guia para Windows 10 (do zero)

> **⚠️ DEPRECADO** — Este guia exige SSH e configuração manual.  
> **Use Railway em vez disso:** [deploy-railway.md](deploy-railway.md) (zero SSH, ~5 passos).

Este guia é para quem **nunca conectou em um servidor antes**.
Siga **um passo de cada vez**. Não pule etapas.

---

## Antes de começar — o que você precisa ter em mãos

1. **Conta na Hetzner** com o servidor já criado (Ubuntu 24.04).
2. **O IP do servidor** — número com pontos, tipo `123.45.67.89`.
   - Abra o navegador → [console.hetzner.cloud](https://console.hetzner.cloud)
   - Clique no seu projeto → clique no servidor
   - Copie o número que aparece em **IPv4**
3. **A senha do servidor** — chegou no e-mail da Hetzner quando você criou o servidor  
   *(ou uma chave SSH, se você configurou uma no painel)*.
4. **A URL do repositório no GitHub** — algo como:  
   `https://github.com/SEU_USUARIO/AI-Commerce-OS.git`  
   *(substitua `SEU_USUARIO` pelo seu usuário real do GitHub)*.

Anote o IP em um bloco de notas. Você vai usar várias vezes.

---

## PARTE A — Preparar o Windows para conectar (só na primeira vez)

### Passo 1 — Ver se o Windows já tem SSH

1. Pressione a tecla **Windows** no teclado (logo do Windows).
2. Digite: `PowerShell`
3. Clique em **Windows PowerShell** (não precisa ser "Administrador").

Uma janela azul ou preta vai abrir. Isso é o **terminal**.

4. Digite exatamente isto e pressione **Enter**:

```
ssh -V
```

**Se deu certo**, aparece algo como:
```
OpenSSH_for_Windows_8.x ...
```

**Se deu errado**, aparece:
```
'ssh' não é reconhecido como comando...
```

→ Se deu errado, vá para o **Passo 2**.  
→ Se deu certo, pule direto para a **PARTE B — Passo 1**.

---

### Passo 2 — Instalar o SSH no Windows (só se o Passo 1 falhou)

1. Pressione **Windows + I** (abre Configurações).
2. Clique em **Aplicativos**.
3. Clique em **Recursos opcionais** (ou **Recursos opcionais / Mais recursos**).
4. Clique em **Adicionar um recurso** (ou **Exibir recursos**).
5. Na busca, digite: `OpenSSH`
6. Marque **Cliente OpenSSH**.
7. Clique em **Instalar**.
8. **Feche** o PowerShell e **abra de novo** (Passo 1 da Parte A).
9. Digite `ssh -V` de novo — agora deve funcionar.

**Alternativa (terminal mais bonito, opcional):**  
Baixe o **Windows Terminal** em:  
[https://apps.microsoft.com/detail/9n0dx20hk701](https://apps.microsoft.com/detail/9n0dx20hk701)  
Depois de instalar, abra **Terminal** em vez do PowerShell. Os comandos são os mesmos.

---

## PARTE B — Conectar no servidor pela primeira vez

### Passo 1 — Abrir o terminal no Windows

1. Pressione **Windows**.
2. Digite: `PowerShell`
3. Clique em **Windows PowerShell**.

Uma janela com texto e um cursor piscando vai aparecer.  
Exemplo do que você vê:
```
PS C:\Users\SeuNome>
```

Isso significa que o terminal está pronto.

---

### Passo 2 — Conectar no servidor

1. **Substitua** `123.45.67.89` pelo IP real que você copiou da Hetzner.
2. Copie o comando abaixo, cole no PowerShell e pressione **Enter**:

```
ssh root@123.45.67.89
```

**Na primeira vez**, pode aparecer uma pergunta assim:
```
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

3. Digite `yes` e pressione **Enter**.

**Depois**, vai pedir a senha:
```
root@123.45.67.89's password:
```

4. Cole a senha que veio no e-mail da Hetzner.  
   *(Ao digitar/colar a senha, **nada aparece na tela** — isso é normal. Pressione Enter mesmo assim.)*

**Se deu certo**, o texto muda para algo como:
```
root@ubuntu-4gb-fsn1-1:~#
```

Você está **dentro do servidor**. A partir daqui, todos os comandos rodam **no servidor**, não no seu PC.

**Se deu errado:**

| O que apareceu | O que fazer |
|---|---|
| `Connection timed out` ou `Connection refused` | Confira se o IP está certo. No painel Hetzner, o servidor precisa estar **Running** (verde). |
| `Permission denied` | Senha errada. Copie de novo do e-mail da Hetzner. |
| `'ssh' não é reconhecido` | Volte à **Parte A — Passo 2** e instale o OpenSSH. |

---

## PARTE C — Clonar o projeto no servidor

> Você ainda está conectado no servidor (vê `root@...` no início da linha).

### Passo 1 — Baixar o projeto do GitHub

1. **Substitua** a URL abaixo pela URL real do seu repositório no GitHub.
2. Copie, cole e pressione **Enter**:

```
git clone https://github.com/SEU_USUARIO/AI-Commerce-OS.git /opt/ai-commerce-os
```

**Se deu certo**, aparecem várias linhas terminando com algo como:
```
Cloning into '/opt/ai-commerce-os'...
Receiving objects: 100% ...
```

**Se deu errado:**

| O que apareceu | O que fazer |
|---|---|
| `Repository not found` | A URL do GitHub está errada ou o repositório é privado sem acesso. |
| `git: command not found` | Digite `apt-get update && apt-get install -y git` e tente de novo. |

---

## PARTE D — Rodar o setup automático

### Passo 1 — Entrar na pasta do projeto

Copie, cole e pressione **Enter**:

```
cd /opt/ai-commerce-os
```

**Se deu certo**, nada de especial aparece — só o cursor volta.  
O caminho pode mudar para algo como `root@...:/opt/ai-commerce-os#`.

---

### Passo 2 — Rodar o script de instalação

Copie, cole e pressione **Enter**:

```
bash infra/setup_cloud_vm.sh
```

**Aguarde.** Na primeira vez pode levar **5 a 15 minutos**.  
Vão aparecer várias linhas — instalação do Docker, download de imagens, etc.

**Se deu certo**, no final aparece algo parecido com isto:

```
=== Setup concluído ===

  API:  http://123.45.67.89:8000/api/v1/health
  Docs: http://123.45.67.89:8000/api/docs

No seu PC, configure o .env local:
  CLOUD_API_URL=http://123.45.67.89:8000
  CLOUD_API_KEY=abc123def456...
```

Anote o endereço da **API** e a **CLOUD_API_KEY** que aparecem aí.

**Se deu errado:**

| O que apareceu | O que fazer |
|---|---|
| `Permission denied` | Digite `chmod +x infra/setup_cloud_vm.sh` e rode o comando de novo. |
| Para no meio com erro de Docker | Espere 2 minutos e rode de novo: `bash infra/setup_cloud_vm.sh` |
| `fatal: could not read Username` | O repositório é privado — configure acesso Git na VM ou use repositório público. |

---

## PARTE E — Pegar a chave de API gerada

### Passo 1 — Mostrar a chave no terminal

Ainda no servidor, copie, cole e pressione **Enter**:

```
grep PIPELINE_API_KEY /opt/ai-commerce-os/.env
```

**Se deu certo**, aparece **uma linha** assim:
```
PIPELINE_API_KEY=a1b2c3d4e5f6789012345678901234ab
```

**Copie só a parte depois do `=`** (as letras e números).  
Guarde no bloco de notas — você vai colar no `.env` do seu PC.

**Se deu errado:**

| O que apareceu | O que fazer |
|---|---|
| Linha vazia ou `PIPELINE_API_KEY=` | Rode de novo: `bash infra/setup_cloud_vm.sh` |
| `No such file` | O clone falhou — volte à **Parte C**. |

---

### Passo 2 — Confirmar que o servidor está respondendo (opcional mas recomendado)

Ainda no servidor:

```
curl http://localhost:8000/api/v1/health
```

**Se deu certo**, aparece algo como:
```
{"status":"ok","version":"..."}
```

---

### Passo 3 — Sair do servidor

Quando terminar, digite:

```
exit
```

Você volta para o PowerShell do Windows (`PS C:\Users\...>`).

---

## PARTE F — Configurar o `.env` no seu PC (Windows)

### Passo 1 — Abrir a pasta do projeto no Windows

1. Abra o **Explorador de Arquivos** (ícone de pasta na barra).
2. Vá até a pasta onde o projeto está no seu PC, por exemplo:  
   `C:\Projetos\AI-Commerce-OS`

---

### Passo 2 — Abrir o arquivo `.env`

1. Na pasta do projeto, procure o arquivo **`.env`**.  
   *(Se não existir, copie `.env.example`, cole na mesma pasta e renomeie a cópia para `.env`.)*
2. Clique com o **botão direito** em `.env` → **Abrir com** → **Bloco de notas**.

**Dica:** Se não enxergar o `.env`, no Explorador clique em **Exibir** → marque **Itens ocultos**.

---

### Passo 3 — Adicionar as linhas da nuvem

Role até o final do arquivo (ou procure a seção `# --- Pipeline na nuvem`).

**Substitua** `123.45.67.89` pelo IP real da Hetzner.  
**Substitua** `COLE_SUA_CHAVE_AQUI` pela chave que você copiou no Passo E.

Adicione ou edite estas duas linhas:

```
CLOUD_API_URL=http://123.45.67.89:8000
CLOUD_API_KEY=COLE_SUA_CHAVE_AQUI
```

Exemplo preenchido:
```
CLOUD_API_URL=http://123.45.67.89:8000
CLOUD_API_KEY=a1b2c3d4e5f6789012345678901234ab
```

1. **Arquivo** → **Salvar**
2. Feche o Bloco de notas.

---

## PARTE G — Teste final no seu PC

### Passo 1 — Abrir o PowerShell de novo

Windows → digite `PowerShell` → abrir.

---

### Passo 2 — Ir até a pasta do projeto

Substitua o caminho se o seu for diferente:

```
cd C:\Projetos\AI-Commerce-OS
```

---

### Passo 3 — Testar a conexão com a nuvem

```
python scripts/cloud/gerar_video.py --topic "teste de conexão"
```

**Se o deploy funcionou**, você verá algo como:

```
✓ Servidor online — versão ...
Enviando pedido para a nuvem...
```

O vídeo de teste pode levar muito tempo para terminar — **não precisa esperar o vídeo inteiro**.  
Se apareceu **"✓ Servidor online"**, a conexão entre seu PC e o servidor está **funcionando**.

**Se deu errado:**

| O que apareceu | O que fazer |
|---|---|
| `Não foi possível conectar` ou `Connection refused` | Confira `CLOUD_API_URL` no `.env`. No painel Hetzner, abra a **porta 8000** no firewall. |
| `401` ou `Unauthorized` | `CLOUD_API_KEY` no PC não bate com `PIPELINE_API_KEY` no servidor — copie de novo (Parte E). |
| `'python' não é reconhecido` | Python não está instalado ou não está no PATH. Instale em [python.org](https://www.python.org/downloads/) marcando **Add Python to PATH**. |

---

## Como saber que tudo está rodando na nuvem

Marque ✅ quando cada item for verdadeiro:

| Onde | O que você deve ver |
|---|---|
| **Painel Hetzner** | Servidor com status **Running** (verde) |
| **SSH no servidor** | `curl http://localhost:8000/api/v1/health` → `{"status":"ok"...}` |
| **Navegador no PC** | Abra `http://SEU_IP:8000/api/docs` — página com documentação da API |
| **PowerShell no PC** | `python scripts/cloud/gerar_video.py --topic "teste"` → **✓ Servidor online** |

Se os quatro itens acima funcionam, o projeto **está rodando na nuvem** e seu PC já pode mandar trabalhos para lá sem processar vídeo localmente.

---

## Resumo rápido (só os comandos, na ordem)

**No PowerShell do Windows (conectar):**
```
ssh root@SEU_IP
```

**No servidor (instalar):**
```
git clone https://github.com/SEU_USUARIO/AI-Commerce-OS.git /opt/ai-commerce-os
cd /opt/ai-commerce-os
bash infra/setup_cloud_vm.sh
grep PIPELINE_API_KEY /opt/ai-commerce-os/.env
exit
```

**No `.env` do PC:**
```
CLOUD_API_URL=http://SEU_IP:8000
CLOUD_API_KEY=chave_copiada_do_servidor
```

**Teste no PC:**
```
cd C:\Projetos\AI-Commerce-OS
python scripts/cloud/gerar_video.py --topic "teste de conexão"
```
