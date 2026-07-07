# AI-Commerce-OS Architecture

## Visão Geral

O AI-Commerce-OS será construído como um sistema modular de automação utilizando Inteligência Artificial.

A ideia principal é separar responsabilidades:

- Automação controla o fluxo.
- Código executa tarefas específicas.
- IA toma decisões inteligentes.
- Banco armazena informações.

---

# Arquitetura Inicial

Fluxo principal:
Fonte de Produtos
|
v
Coletor de Dados
|
v
Analisador com IA
|
v
Banco de Dados
|
v
Gerador de Conteúdo
|
v
Publicação

---

# Componentes

## 1. n8n - Orquestração

Responsabilidade:

- Controlar automações.
- Executar workflows.
- Conectar serviços.

O n8n será o "maestro" do sistema.

---

## 2. Scripts

Pasta:
scripts/


Responsabilidade:

- Executar lógica personalizada.
- Fazer tratamentos de dados.
- Integrar APIs.

---

## 3. IA

Responsabilidade:

- Avaliar produtos.
- Criar análises.
- Gerar textos e ideias.

A IA será utilizada como camada de decisão.

---

## 4. Banco de Dados

Pasta:
database/


Responsabilidade:

Guardar:

- Produtos encontrados.
- Análises realizadas.
- Histórico de resultados.

---

## 5. Workflows

Pasta:
workflows/

Responsabilidade:

Guardar os fluxos de automação.

Exemplo:
buscar-produtos.json
analisar-produtos.json
gerar-conteudo.json


---

# Princípios do Projeto

## Modularidade

Cada parte do sistema deve poder ser substituída sem quebrar tudo.

Exemplo:

Trocar Gemini por outra IA não deve exigir reconstruir o projeto inteiro.

---

## Escalabilidade

O projeto deve conseguir crescer de uma automação simples para uma plataforma completa.

---

## Reutilização

Componentes criados devem poder ser utilizados em outros projetos.

---

# Objetivo da Sprint 2

Construir o primeiro módulo:

Product Hunter.

Responsável por:

- Receber informações de produtos.
- Organizar dados.
- Preparar análise por IA.