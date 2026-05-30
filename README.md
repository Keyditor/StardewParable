# 🌾 StardewParable — *Sua Fazenda Está Sendo Julgada*

<p align="center">

*"Esta é a história de um fazendeiro chamado..."*

**Um mod narrativo com IA para Stardew Valley inspirado em The Stanley Parable**

</p>

---

# 🇧🇷 Português

## 📖 Sobre

**StardewParable** é um mod focado em narrativa para Stardew Valley inspirado em *The Stanley Parable*.

Em vez de apenas observar silenciosamente suas decisões questionáveis na fazenda, o mod registra suas ações durante o dia e as transforma em narrações sarcásticas geradas por IA.

Cada dia se torna uma história.

Cada erro se torna entretenimento.

---

## ✨ Funcionalidades

### 🎮 Rastreamento de Gameplay

Registra automaticamente:

- Ações agrícolas
- Uso de ferramentas
- Mineração
- Pesca
- Interações com NPCs
- Transições de áreas
- Crafting
- Cutscenes
- Comportamento geral do jogador

### 🧠 Geração Narrativa com IA

Suas ações são transformadas em:

- Resumos narrativos dinâmicos
- Comentários sarcásticos
- Histórias únicas diariamente
- Narração contextual

Compatível com:

- APIs compatíveis com OpenAI
- Groq
- Provedores self-hosted compatíveis

### 🔊 Narração por Voz

As histórias geradas são:

- Convertidas automaticamente em voz
- Reproduzidas no final do dia
- Personalizáveis com vozes próprias

---

## 🏗 Arquitetura do Projeto

```text
┌─────────────────────┐
│ Mod Stardew Valley  │
│     (SMAPI/C#)      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Backend FastAPI     │
│ Construção Prompt   │
│ Geração LLM         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Serviço TTS         │
│ Síntese de Voz      │
└──────────┬──────────┘
           │
           ▼
🎙 Narração Final
```

---

## 📦 Estrutura

```text
StardewParable/
│
├── ActionLogger/
├── backend/
├── prompts.json
└── README.md
```

---

## 🚀 Instalação

### Requisitos

- Stardew Valley
- SMAPI
- Python 3.8+
- Serviço TTS rodando
- Chave API LLM

### Instalar o Mod

Copie:

```text
ActionLogger/bin/Debug/net6.0/
```

Para:

```text
Stardew Valley/Mods/
```

### Backend

```bash
cd backend
pip install -r requirements.txt
```

Configure:

```env
OPENAI_API_BASE=https://api.groq.com/openai/v1
OPENAI_API_KEY=SUA_CHAVE
OPENAI_MODEL=llama-3.1-8b-instant
TTS_API_URL=https://seu-servico-tts/synthesize
```

Execute:

```bash
uvicorn main:app --reload --port 8000
```

---

## 🎮 Como Usar

Jogue normalmente.

Ao dormir:

1. Suas ações são coletadas
2. Enviadas ao backend
3. A IA gera uma história
4. O TTS sintetiza a voz
5. Suas escolhas são julgadas

---

## 🛣 Roadmap

- [ ] Mais personalidades de narrador
- [ ] Suporte multilíngue
- [ ] Suporte a LLMs locais
- [ ] Melhor memória contextual
- [ ] Multiplayer
- [ ] Pacotes de voz

---

## 🤝 Contribuição

Contribuições são bem-vindas.

Abra issues, sugira funcionalidades ou envie pull requests.

---

# 🇺🇸 English

## 📖 About

**StardewParable** is a narrative-focused mod for Stardew Valley inspired by *The Stanley Parable*.

Instead of silently observing your questionable farming decisions, the mod records your actions throughout the day and transforms them into sarcastic AI-generated narrations.

Every day becomes a story.

Every mistake becomes entertainment.

---

## ✨ Features

### 🎮 Gameplay Tracking

Automatically records:

- Farming actions
- Tool usage
- Mining
- Fishing
- NPC interactions
- Area transitions
- Crafting
- Cutscenes
- General player behavior

### 🧠 AI Narrative Generation

Transforms your actions into:

- Dynamic narrative summaries
- Sarcastic commentary
- Unique daily stories
- Context-aware narration

Supports:

- OpenAI compatible APIs
- Groq
- Compatible self-hosted providers

### 🔊 Voice Narration

Generated stories are:

- Automatically converted to speech
- Played at the end of the day
- Customizable with your own voices

---

## 🏗 Project Architecture

```text
┌─────────────────────┐
│ Stardew Valley Mod  │
│      (SMAPI/C#)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ FastAPI Backend     │
│ Prompt Building     │
│ LLM Generation      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ TTS Service         │
│ Voice Synthesis     │
└──────────┬──────────┘
           │
           ▼
🎙 Narrated Story
```

---

## 🚀 Installation

### Requirements

- Stardew Valley
- SMAPI
- Python 3.8+
- Running TTS Service
- LLM API Key

### Backend

```bash
cd backend
pip install -r requirements.txt
```

Configure:

```env
OPENAI_API_BASE=https://api.groq.com/openai/v1
OPENAI_API_KEY=YOUR_KEY
OPENAI_MODEL=llama-3.1-8b-instant
TTS_API_URL=https://your-tts-service/synthesize
```

Run:

```bash
uvicorn main:app --reload --port 8000
```

---

> *"He watered the crops again. As if routine could somehow fill the emptiness."*  
> — The Narrator
