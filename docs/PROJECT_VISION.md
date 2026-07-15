# AI-Commerce-OS

## Visão

O AI-Commerce-OS é um motor de produção de conteúdo para TikTok Shop.

Seu objetivo é automatizar o processo completo de descoberta de produtos, criação de estratégias, geração de conteúdo e produção de vídeos curtos prontos para publicação.

A IA não é o produto.

Ela é apenas uma ferramenta utilizada em algumas etapas do pipeline.

O verdadeiro produto é um sistema capaz de transformar um produto em diversos conteúdos para testar no TikTok Shop.

---

# Objetivo da V1

A versão 1 deve ser capaz de:

- Encontrar produtos.
- Analisar potencial de venda.
- Definir uma estratégia de conteúdo.
- Gerar roteiro.
- Gerar narração.
- Buscar mídia.
- Gerar legendas.
- Renderizar vídeo.
- Exportar vídeo pronto.

Tudo isso de forma automática.

---

# Escopo Atual

Nesta fase o projeto trabalhará exclusivamente com TikTok Shop.

Toda funcionalidade relacionada à Shopee está congelada e não deve ser utilizada.

O módulo Persona IA também permanece congelado até a conclusão da V1.

---

# Filosofia

O projeto deve ser modular.

Cada módulo possui apenas uma responsabilidade.

Evitar acoplamento.

Evitar lógica duplicada.

Evitar chamadas de IA espalhadas pelo projeto.

---

# Arquitetura Desejada

O sistema será dividido em motores independentes.

## Discovery Engine

Responsável por descobrir produtos.

Entrada:

- TikTok Shop
- Trends
- Hashtags

Saída:

Produto normalizado.

---

## Analysis Engine

Responsável por analisar o produto.

Saída:

- score
- público
- diferenciais
- oportunidades

---

## Strategy Engine

Responsável por decidir COMO vender o produto.

Exemplos:

- review
- curiosidade
- antes e depois
- teste
- comparação
- unboxing

O resultado deste módulo deve ser reutilizável.

---

## Script Engine

Recebe a estratégia.

Produz o roteiro.

---

## Content Engine

Produz:

- narração
- descrição
- hashtags
- CTA

---

## Scene Engine

Planeja todas as cenas do vídeo.

Não baixa mídia.

Apenas define o que precisa aparecer.

---

## Asset Engine

Busca ou gera imagens e vídeos.

---

## Audio Engine

Gera a narração.

---

## Subtitle Engine

Gera legendas.

---

## Render Engine

Recebe:

- cenas
- áudio
- legendas

Produz:

video.mp4

Nunca deve conhecer IA.

---

## Export Engine

Organiza todos os arquivos finais.

---

# Fluxo Desejado

Trend Discovery

↓

Product Discovery

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

---

# Objetivo Final

O AI-Commerce-OS NÃO deve produzir apenas um vídeo.

Ele deve produzir diversas variações automaticamente.

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

Cada vídeo possui um hook diferente, uma abordagem diferente e um CTA diferente.

O objetivo é gerar conteúdos suficientes para testar qual possui maior conversão no TikTok Shop.

---

# Regras para Desenvolvimento

Antes de qualquer alteração:

- entender a arquitetura existente;
- preservar funcionalidades atuais;
- evitar reescrever módulos inteiros;
- modificar apenas os arquivos necessários;
- fazer alterações pequenas;
- manter compatibilidade.

Nunca criar funcionalidades que não estejam alinhadas com esta visão.

---

# Princípios

- Simplicidade.
- Modularidade.
- Escalabilidade.
- Reutilização.
- Automação.
- Fácil manutenção.
- Baixo custo operacional.
- Compatibilidade com APIs gratuitas.

Toda decisão de arquitetura deve seguir estes princípios.