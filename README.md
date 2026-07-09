# AI-Commerce-OS

> Sistema inteligente de automação para descoberta de produtos, análise de oportunidades e criação de conteúdo para TikTok Commerce.

## Visão Geral

O AI-Commerce-OS é uma plataforma de automação baseada em inteligência artificial criada para transformar uma ideia de produto em um pacote completo de conteúdo comercial.

O sistema analisa produtos, avalia potencial de venda, cria roteiros, gera narração, monta cenas, busca mídias e renderiza vídeos automaticamente.

O objetivo é reduzir o trabalho manual necessário para criação de conteúdo de e-commerce e permitir testes rápidos de novos produtos.

---

# Funcionalidades Atuais

## 🔎 Pesquisa e Análise de Produtos

* Coleta de produtos.
* Análise de potencial comercial usando IA.
* Avaliação de oportunidade.
* Sistema de pontuação e ranking.

---

## 🧠 Inteligência Artificial

* Geração automática de análises.
* Criação de roteiros UGC (User Generated Content).
* Geração de textos comerciais.
* Sistema de cache para reduzir chamadas de IA.

---

## 🎬 Produção Automática de Vídeos

O sistema gera:

* Estrutura de cenas.
* Busca de assets visuais.
* Download de vídeos/imagens.
* Narração automática com Text-To-Speech.
* Legendas sincronizadas.
* Renderização final em MP4.

---

## 📦 Exportação

Cada produto gera um pacote contendo:

* Análise do produto.
* Oportunidade comercial.
* Roteiro.
* Conteúdo.
* Legendas.
* Assets utilizados.
* Vídeo final.

---

# Arquitetura

```
Produto
   |
   ↓
Coleta
   |
   ↓
Análise IA
   |
   ↓
Score + Ranking
   |
   ↓
Decisão
   |
   ↓
Roteiro
   |
   ↓
Conteúdo
   |
   ↓
Assets
   |
   ↓
Áudio + Legendas
   |
   ↓
Renderização
   |
   ↓
Vídeo Final
```

---

# Tecnologias

* Python
* FFmpeg
* Edge-TTS
* Google Gemini
* Docker
* n8n
* Git
* GitHub
* VS Code

---

# Estrutura do Projeto

```
AI-Commerce-OS/

├── scripts/
│   ├── ai/
│   ├── audio/
│   ├── content/
│   ├── video/
│   ├── pipeline/
│   └── publisher/
│
├── database/
│
├── prompts/
│
├── output/
│
└── main.py
```

---

# Status

🚧 Versão inicial funcional.

Atualmente o sistema já consegue:

✅ Analisar produtos com IA
✅ Gerar conteúdo comercial
✅ Criar vídeos automaticamente
✅ Gerar áudio e legendas
✅ Exportar resultados

---

# Roadmap

## Versão 0.2

* [ ] Sistema de logs.
* [ ] Configuração centralizada.
* [ ] Estado dos produtos.
* [ ] Melhor sincronização entre cenas e áudio.
* [ ] Dashboard avançado.

## Versão 0.3

* [ ] Integração completa com n8n.
* [ ] Publicação automática.
* [ ] Monitoramento de tendências.
* [ ] Aprendizado baseado em resultados.

---

# Autor

Projeto desenvolvido como estudo e construção de uma plataforma de automação com IA aplicada ao comércio digital.
