# AI-Commerce-OS Context

> Leia este documento antes de analisar ou modificar qualquer arquivo deste projeto.

---

# Visão do Projeto

O AI-Commerce-OS NÃO é um gerador de vídeos baseado em IA.

O objetivo do projeto é ser um Motor de Produção de Conteúdo para TikTok Shop.

A IA é apenas uma ferramenta dentro do pipeline.

O produto final do sistema é produzir automaticamente vídeos de alta qualidade para TikTok Shop utilizando produtos encontrados automaticamente.

O foco do projeto é:

- descobrir produtos
- analisar oportunidades
- definir estratégia
- gerar conteúdo
- produzir vídeos
- exportar vídeos prontos

Não focar apenas em geração de texto.

---

# Objetivo da V1

A primeira versão deve ser capaz de:

1. Encontrar produtos.

2. Escolher apenas produtos promissores.

3. Criar uma estratégia de conteúdo.

4. Gerar roteiro.

5. Gerar narração.

6. Buscar mídia.

7. Gerar legendas.

8. Renderizar vídeo.

9. Exportar um vídeo final pronto para publicação.

Qualquer funcionalidade que não contribua diretamente para esse fluxo deve ser considerada fora da V1.

---

# Escopo Atual

TikTok Shop apenas.

Shopee foi removida temporariamente.

Não adicionar novamente nenhuma funcionalidade relacionada à Shopee.

---

# Persona IA

O módulo Persona IA está congelado.

Não modificar.

Não criar novas funcionalidades para ele.

Toda mídia da V1 deve utilizar apenas vídeos/imagens existentes (Stock).

---

# Arquitetura Desejada

O sistema deve evoluir para motores independentes.

Discovery Engine

↓

Analysis Engine

↓

Strategy Engine

↓

Script Engine

↓

Content Engine

↓

Scene Engine

↓

Asset Engine

↓

Audio Engine

↓

Subtitle Engine

↓

Render Engine

↓

Export Engine

Cada motor deve possuir responsabilidade única.

---

# Estado Atual do Projeto

A auditoria realizada encontrou aproximadamente:

- 98 arquivos Python
- 59 módulos

Principais pontos identificados:

## Pipeline

Existe um pipeline funcional.

Porém o Strategy Engine ainda não participa efetivamente do fluxo.

Esta é uma das prioridades atuais.

---

## Duplicações

Existem módulos com responsabilidades semelhantes.

Exemplos:

- script_generator.py
- ai_script_generator.py

- analyst.py
- ai_analyst.py

Essas duplicações devem ser eliminadas apenas quando não quebrarem compatibilidade.

Nunca remover código sem confirmar que ele não é utilizado.

---

## Renderer

O Render Engine deve conhecer apenas:

- cenas
- áudio
- legendas

Ele NÃO deve conhecer:

- IA
- produto
- prompts
- estratégia

---

## IA

Toda lógica de IA deve ficar isolada.

Não espalhar chamadas Gemini pelo projeto.

Sempre reutilizar a camada existente.

---

## Banco

Atualmente os JSON funcionam como armazenamento.

Não migrar para banco SQL antes da V2.

---

## Objetivo Arquitetural

O projeto deve transformar:

Produto

↓

Estratégia

↓

Diversos conteúdos

↓

Diversos vídeos

↓

Exportação

e NÃO apenas:

Produto

↓

Vídeo

Um único produto deve conseguir gerar diversas estratégias de conteúdo.

Exemplo:

Produto:

Mini Aspirador

↓

Estratégia 1

↓

Vídeo 1

Estratégia 2

↓

Vídeo 2

Estratégia 3

↓

Vídeo 3

Estratégia 4

↓

Vídeo 4

---

# Regras para Alterações

Nunca reescreva o projeto.

Sempre evolua incrementalmente.

Nunca invente arquivos existentes.

Nunca invente estruturas.

Sempre analisar o código existente.

Antes de alterar:

1. Identifique quais arquivos realmente precisam ser modificados.

2. Explique o motivo.

3. Faça alterações mínimas.

4. Preserve compatibilidade.

5. Não faça refatorações desnecessárias.

6. Não alterar mais de 3 arquivos por tarefa.

7. Não modificar código fora do escopo solicitado.

---

# Prioridades Atuais

PRIORIDADE 1

Integrar corretamente o Strategy Engine ao pipeline.

---

PRIORIDADE 2

Eliminar dependências da Shopee.

---

PRIORIDADE 3

Simplificar o pipeline.

---

PRIORIDADE 4

Melhorar tratamento de erros.

---

PRIORIDADE 5

Adicionar logging estruturado.

---

PRIORIDADE 6

Melhorar coleta de produtos.

---

PRIORIDADE 7

Preparar publicação automática (V2).

---

# Backlog Arquitetural

Melhorias de qualidade arquitetural adiadas em favor de funcionalidades da V1.

## Contrato público do Strategy Engine (sprint futura)

Formalizar a saída de `generate_creative_strategy` como contrato estável
para os motores downstream (Script, Content, Scene, Render).

Escopo proposto:

- `CreativeStrategy` como TypedDict (7 campos atuais + `schema_version`)
- Enums documentados para `angulo` e `estilo_video`
- Função `validate_creative_strategy()` (validação leve, sem transformação)
- Validação na saída do Strategy Engine
- Exportar `strategy.json` no pacote de exportação
- Mapeamento de nomenclatura legada (`hook` ↔ `gancho`, `angulos` ↔ `angulo`)

Não implementar nesta sprint.

Motivo: aumenta qualidade arquitetural, mas não aumenta capacidade
de produção de conteúdo na V1.

---

# Forma de Trabalho

Sempre trabalhar em pequenas tarefas.

Fluxo obrigatório:

Analisar

↓

Planejar

↓

Explicar

↓

Modificar

↓

Aguardar confirmação

Nunca modificar vários módulos ao mesmo tempo.

Nunca fazer alterações em massa.

Sempre preservar o máximo possível do código existente.