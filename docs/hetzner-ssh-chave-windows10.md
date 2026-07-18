# Conectar na Hetzner com chave SSH — Windows 10 (do zero)

Este guia é para quem **nunca configurou chave SSH** e recebe este erro ao tentar entrar no servidor:

```
Permission denied (publickey,password)
```

Isso significa: o servidor **não aceita senha pelo SSH** — só aceita **chave SSH**.  
Siga **um passo de cada vez**. Não pule etapas.

**IP do servidor deste guia:** `138.199.175.143`  
**Usuário:** `root`

---

## O que vamos fazer (visão geral)

1. Criar uma “chave digital” no seu PC (grátis, leva 1 minuto).
2. Cadastrar essa chave no painel da Hetzner.
3. Colocar a chave **dentro do servidor** (passo obrigatório se o servidor já existia antes).
4. Conectar pelo terminal com o comando certo.
5. Confirmar que funcionou.

---

## PASSO 1 — Abrir o terminal no Windows

1. Pressione a tecla **Windows** no teclado.
2. Digite: `PowerShell`
3. Clique em **Windows PowerShell** (não precisa ser “Administrador”).

**O que você deve ver na tela:**

```
PS C:\Users\SeuNome>
```

O cursor piscando no final da linha significa que o terminal está pronto.

---

## PASSO 2 — Confirmar que o SSH já vem no Windows

Copie e cole **só esta linha** no PowerShell. Depois pressione **Enter**:

```
ssh -V
```

**Se deu certo**, aparece algo parecido com:

```
OpenSSH_for_Windows_9.5p1, LibreSSL 3.8.2
```

(O número da versão pode ser diferente — tudo bem.)

**Se deu errado**, aparece:

```
'ssh' não é reconhecido como nome de cmdlet...
```

→ Nesse caso, instale o **Cliente OpenSSH** em:  
**Configurações do Windows** → **Aplicativos** → **Recursos opcionais** → **Adicionar um recurso** → busque **OpenSSH Client** → **Instalar**.  
Feche o PowerShell, abra de novo e repita `ssh -V`.

---

## PASSO 3 — Gerar a chave SSH no seu PC

Copie e cole **só esta linha**. Pressione **Enter**:

```
ssh-keygen -t ed25519 -C "meu-pc-windows"
```

O programa vai fazer **3 perguntas**. Responda assim:

### Pergunta 1 — Onde salvar a chave

Aparece:

```
Enter file in which to save the key (C:\Users\SeuNome/.ssh/id_ed25519):
```

**Só pressione Enter** (aceita o caminho padrão).

### Pergunta 2 — Senha da chave (passphrase)

Aparece:

```
Enter passphrase (empty for no passphrase):
```

**Só pressione Enter** (sem senha — mais simples para começar).

### Pergunta 3 — Repetir a senha

Aparece:

```
Enter same passphrase again:
```

**Só pressione Enter** de novo.

**Se deu certo**, no final aparecem linhas como:

```
Your identification has been saved in C:\Users\SeuNome\.ssh\id_ed25519
Your public key has been saved in C:\Users\SeuNome\.ssh\id_ed25519.pub
The key fingerprint is:
SHA256:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx meu-pc-windows
The key's randomart image is:
+--[ED25519 256]--+
|     ...         |
+----[SHA256]-----+
```

A parte importante: foram criados **dois arquivos** na pasta `.ssh` do seu usuário:

| Arquivo | O que é | Pode compartilhar? |
|---------|---------|-------------------|
| `id_ed25519` | Chave **privada** (secreta) | **Nunca** |
| `id_ed25519.pub` | Chave **pública** | Sim — vai para a Hetzner |

---

## PASSO 4 — Copiar a chave pública para a área de transferência

Copie e cole **só esta linha**. Pressione **Enter**:

```
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub | Set-Clipboard
```

**Se deu certo:** nada especial aparece — a chave já está copiada (Ctrl+V).

Para **ver** a chave na tela (opcional), rode:

```
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub
```

**Se deu certo**, aparece **uma linha longa** começando com:

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI...
```

Essa linha inteira é a sua **chave pública**. Você vai colar ela no painel da Hetzner no próximo passo.

---

## PASSO 5 — Cadastrar a chave no painel da Hetzner

Abra o navegador e siga **clicando exatamente nesta ordem**:

### 5.1 — Entrar no painel

1. Abra: [https://console.hetzner.cloud](https://console.hetzner.cloud)
2. Faça login na sua conta Hetzner (e-mail e senha da conta Hetzner — **não** é a senha do servidor).

### 5.2 — Ir até o projeto certo

3. Na tela inicial, você vê **caixas com nomes de projetos** (ex.: “default”, “Production”, etc.).
4. **Clique** no projeto onde está o seu servidor.

### 5.3 — Abrir a área de chaves SSH

5. No **menu lateral esquerdo**, procure **Security** (ou **Segurança**).
6. **Clique** em **Security**.
7. Na sublista que abre, **clique** em **SSH Keys**.

**O que você deve ver:** uma página com título **SSH Keys**, um botão vermelho **Add SSH Key** (ou **Adicionar chave SSH**) e, se for a primeira chave, a lista vazia.

### 5.4 — Adicionar a chave

8. **Clique** no botão vermelho **Add SSH Key**.
9. Abre um formulário com dois campos:
   - **Name** (Nome): digite algo fácil de lembrar, por exemplo `PC-Windows-Dono`
   - **Public key** (Chave pública): **clique dentro do campo** e pressione **Ctrl+V** para colar a linha que você copiou no Passo 4
10. Marque a opção **Set as default key** se aparecer (opcional, mas recomendado).
11. **Clique** no botão vermelho **Add SSH Key** (ou **Add**) no canto inferior direito do formulário.

**Se deu certo:** a chave aparece na lista com o nome que você digitou (ex.: `PC-Windows-Dono`) e um fingerprint (código curto tipo `SHA256:...`).

> **Importante:** cadastrar a chave no painel **guarda** ela na Hetzner, mas **não coloca automaticamente** dentro de um servidor que **já estava rodando**. Por isso existe o Passo 6.

---

## PASSO 6 — Colocar a chave dentro do servidor (Console do navegador)

Como o SSH ainda não funciona, usamos o **Console** da Hetzner — um terminal que abre **dentro do navegador**, sem precisar de SSH.

### 6.1 — Abrir o Console do servidor

1. No menu lateral esquerdo, **clique** em **Servers** (ícone de servidor / lista de máquinas).
2. **Clique** no nome do seu servidor na lista (o que tem o IP `138.199.175.143`).
3. Você entra na página **Overview** (Visão geral) do servidor.
4. No canto **superior direito** da página, procure um ícone de **monitor** ou botão **Console**. **Clique** nele.
5. Abre uma janela preta (noVNC) dentro do navegador — é o terminal do servidor.

**O que você deve ver:** tela preta com texto branco, pedindo login, algo como:

```
Ubuntu 24.04.x LTS ubuntu-xxx tty1

ubuntu-xxx login:
```

### 6.2 — Entrar como root

6. Digite `root` e pressione **Enter**.
7. Aparece `Password:` — digite a **senha root** que veio no e-mail da Hetzner quando o servidor foi criado.  
   *(Ao digitar, **nada aparece na tela** — isso é normal. Pressione Enter mesmo assim.)*

**Se deu certo**, o prompt muda para algo como:

```
root@ubuntu-4gb-fsn1-1:~#
```

Você está **dentro do servidor** pelo navegador.

**Se a senha não funcionar:** no painel Hetzner, na página do servidor, vá em **Rescue** → ative o modo rescue com a chave que você cadastrou → reinicie o servidor → conecte via SSH em modo rescue. Se precisar desse caminho, peça ajuda — é menos comum.

### 6.3 — Instalar a chave pública no servidor

Ainda no Console do navegador, rode **um comando de cada vez**.

**Comando 1** — criar a pasta de chaves (se não existir):

```
mkdir -p ~/.ssh
```

**Comando 2** — abrir o editor para colar a chave:

```
nano ~/.ssh/authorized_keys
```

**Comando 3** — dentro do nano:
- Pressione **Ctrl+V** (ou botão direito → Colar) para colar a **mesma linha** `ssh-ed25519 AAAA...` do Passo 4.
- A linha deve ficar **inteira em uma única linha**, sem quebras no meio.
- Pressione **Ctrl+O** (salvar), depois **Enter**.
- Pressione **Ctrl+X** (sair).

**Comando 4** — ajustar permissões (obrigatório para o SSH aceitar):

```
chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys
```

**Comando 5** — confirmar que a chave foi salva:

```
cat ~/.ssh/authorized_keys
```

**Se deu certo**, aparece a linha `ssh-ed25519 AAAAC3... meu-pc-windows`.

**Comando 6** — sair do Console:

```
exit
```

Pode fechar a aba do Console no navegador.

---

## PASSO 7 — Conectar pelo SSH do seu PC

Volte ao **PowerShell** no Windows (Passo 1).

Copie e cole **só esta linha**. Pressione **Enter**:

```
ssh root@138.199.175.143
```

**Na primeira vez**, pode aparecer:

```
The authenticity of host '138.199.175.143' can't be established.
ED25519 key fingerprint is SHA256:...
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

Digite `yes` e pressione **Enter**.

**Se deu certo**, **não pede senha** e o prompt muda para:

```
root@ubuntu-4gb-fsn1-1:~#
```

Parabéns — você entrou no servidor pela chave SSH.

**Se ainda der** `Permission denied (publickey)`:

| Possível causa | O que fazer |
|----------------|-------------|
| Chave não colada certo no Passo 6 | Repita o Passo 6 — a linha em `authorized_keys` deve ser **uma linha só** |
| Chave em outro arquivo | Use: `ssh -i $env:USERPROFILE\.ssh\id_ed25519 root@138.199.175.143` |
| Servidor errado | Confira no painel se o IP é mesmo `138.199.175.143` |

---

## PASSO 8 — Confirmar que a conexão funcionou

Ainda conectado no servidor (vê `root@...` no início da linha), rode **um comando de cada vez**:

**Comando 1** — confirmar usuário e máquina:

```
whoami
```

**Se deu certo:**

```
root
```

**Comando 2** — confirmar nome do servidor:

```
hostname
```

**Se deu certo**, algo como:

```
ubuntu-4gb-fsn1-1
```

**Comando 3** — confirmar IP interno (opcional):

```
hostname -I
```

**Se deu certo**, aparece uma lista de IPs; um deles será `138.199.175.143` (ou próximo).

**Comando 4** — sair e voltar ao Windows:

```
exit
```

**Se deu certo**, você volta ao PowerShell:

```
PS C:\Users\SeuNome>
```

---

## Resumo — comandos para copiar e colar

**No PowerShell (Windows) — gerar e copiar chave:**

```
ssh-keygen -t ed25519 -C "meu-pc-windows"
```

(Pressione Enter nas 3 perguntas.)

```
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub | Set-Clipboard
```

**No PowerShell (Windows) — conectar:**

```
ssh root@138.199.175.143
```

**Dentro do servidor — confirmar:**

```
whoami
hostname
exit
```

---

## Nas próximas vezes

Sempre que quiser entrar no servidor, abra o PowerShell e rode:

```
ssh root@138.199.175.143
```

Não precisa repetir a criação da chave nem o cadastro no painel — isso é **só uma vez**.

---

## Segurança — lembrete rápido

- **Nunca** envie o arquivo `id_ed25519` (sem `.pub`) para ninguém.
- **Nunca** coloque a chave privada no GitHub, WhatsApp ou e-mail.
- Só a linha que termina em `.pub` vai para a Hetzner e para o servidor.
