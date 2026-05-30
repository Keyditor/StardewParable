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

Registra automaticamente, de forma precisa:

- Ações agrícolas (plantio, colheita, rega)
- Colocação de móveis, baús e equipamentos (100% de precisão baseada no inventário)
- Uso de ferramentas e armas
- Mineração e combate a monstros
- Pesca
- Interações com NPCs e cutscenes
- Transições de áreas
- Crafting e vendas de itens
- Comportamento geral do jogador

### 🧠 Geração Narrativa com IA (Continuidade)

Suas ações são transformadas em:

- Resumos narrativos dinâmicos
- Comentários sarcásticos (no estilo *Stanley Parable*)
- Histórias contextuais **com continuidade** (a IA se lembra dos últimos eventos narrados para manter a coesão)

Compatível com:

- APIs compatíveis com OpenAI (incluindo Groq, Llama, ChatGPT, etc.)
- Provedores self-hosted

### ⏳ Modos de Narração (GMCM)

Totalmente integrado ao **Generic Mod Config Menu**. Escolha quando quer ser julgado:

- **Diária:** A narração ocorre apenas no final do dia ou ao dormir.
- **Por Turno:** A narração ocorre ao meio-dia (12:00), no início da noite (18:00) e ao dormir, permitindo uma experiência mais viva e frequente.

### 🔊 Integração de Voz (TTS)

As histórias geradas são lidas em voz alta:

- **ElevenLabs:** Suporte nativo. Adicione sua chave e o ID da voz direto no menu do jogo.
- **Serviço TTS Local:** Suporte a geradores locais próprios rodando via backend.

### 📊 Dashboard Interativo

Acompanha um **Dashboard via Gradio** integrado ao backend, onde você pode:

- Visualizar logs em tempo real das ações enviadas pelo mod
- Acompanhar as narrações geradas e o histórico de contexto mantido pela IA
- Enviar comandos e testar scripts de narração customizados diretamente pelo navegador!

---

## 🏗 Arquitetura do Projeto

```text
┌─────────────────────┐
│ Mod Stardew Valley  │
│ (Ações e Opções)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐       ┌───────────────────────┐
│ Backend FastAPI     │ ────► │ Dashboard Gradio WEB  │
│ Prompt + Memória    │       └───────────────────────┘
│ Geração LLM         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Serviço TTS         │
│ (Local ou ElevenLabs│
└──────────┬──────────┘
           │
           ▼
🎙 Narração Final
```

---

## 🚀 Instalação

### Requisitos

- Stardew Valley
- SMAPI e Generic Mod Config Menu
- Python 3.8+
- Serviço TTS rodando (Opcional caso utilize ElevenLabs)
- Chave API LLM (Opcional se usar Local, obrigatório para OpenAI/Groq)

### Instalar o Mod

Basta dar build ou copiar a pasta compilada:

```text
src/bin/Release/net6.0/ActionLogger 1.3.0/
```

Para a pasta de mods do jogo:

```text
Stardew Valley/Mods/
```

### Backend

Na raiz do projeto, instale as dependências:

```bash
cd backend
pip install -r requirements.txt
```

Configure seu arquivo `.env` base (que atua como fallback caso você não ponha dados no GMCM no jogo):

```env
OPENAI_API_BASE=https://api.groq.com/openai/v1
OPENAI_API_KEY=SUA_CHAVE
OPENAI_MODEL=llama-3.1-8b-instant
TTS_API_URL=http://localhost:5000/synthesize
```

Execute o backend:

```bash
uvicorn main:app --reload --port 8000
```

*Nota: Acesse `http://localhost:8000/dashboard` no navegador para abrir o painel de controle!*

---

## 🎮 Como Usar

1. Inicie o Stardew Valley.
2. Na tela inicial, abra o ícone da engrenagem (**Generic Mod Config Menu**) e procure pelo **Action Logger**.
3. Configure o Modo de Narração (Turno ou Diária).
4. Insira (opcionalmente) suas credenciais da OpenAI ou ElevenLabs direto lá! Se deixado em branco, o mod usará os dados do seu arquivo `.env` na backend.
5. Jogue normalmente. Suas escolhas agora serão devidamente julgadas pelo narrador no horário definido!

---

## 🤝 Contribuição

Contribuições são bem-vindas. Abra issues, sugira funcionalidades ou envie pull requests.

---

# 🇺🇸 English

## 📖 About

**StardewParable** is a narrative-focused mod for Stardew Valley inspired by *The Stanley Parable*.

Instead of silently observing your questionable farming decisions, the mod records your actions and transforms them into sarcastic AI-generated narrations.

Every day becomes a story.

Every mistake becomes entertainment.

---

## ✨ Features

### 🎮 Gameplay Tracking

Automatically and accurately records:

- Farming actions (planting, harvesting, watering)
- Placing furniture, chests, and equipment (100% precision based on inventory reduction)
- Tool and weapon usage
- Mining and fighting
- Fishing
- NPC interactions and cutscenes
- Area transitions
- Crafting and selling
- General player behavior

### 🧠 AI Narrative Generation (Continuity)

Transforms your actions into:

- Dynamic narrative summaries
- Sarcastic commentary
- Context-aware stories **with continuity** (the AI remembers past events to maintain narrative flow)

Supports:

- OpenAI compatible APIs (Groq, ChatGPT, Llama, etc.)
- Compatible self-hosted providers

### ⏳ Narration Modes (GMCM)

Fully integrated into the **Generic Mod Config Menu**. Choose when you want to be judged:

- **Daily:** Narration occurs only at the end of the day or when you sleep.
- **Per Turn:** Narration happens at Noon (12:00), Evening (18:00), and when you sleep, allowing for a more frequent, lively experience.

### 🔊 Voice Narration (TTS)

Generated stories are read aloud:

- **ElevenLabs:** Native support. Add your API key and Voice ID straight from the in-game config menu.
- **Local TTS:** Fallback support for custom local speech synthesizers.

### 📊 Interactive Dashboard

A full **Gradio Web Dashboard** is built into the backend. You can:

- Monitor incoming action logs in real-time
- Check generated narrations and the context memory used by the AI
- Trigger test narrations manually with custom prompts right from the browser!

---

## 🏗 Project Architecture

```text
┌─────────────────────┐
│ Stardew Valley Mod  │
│ (Actions & Options) │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐       ┌───────────────────────┐
│ FastAPI Backend     │ ────► │ Gradio Web Dashboard  │
│ Prompt & Memory     │       └───────────────────────┘
│ LLM Generation      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ TTS Service         │
│(Local or ElevenLabs)│
└──────────┬──────────┘
           │
           ▼
🎙 Narrated Story
```

---

## 🚀 Installation

### Requirements

- Stardew Valley
- SMAPI and Generic Mod Config Menu
- Python 3.8+
- Running TTS Service (Optional if using ElevenLabs)
- LLM API Key (Optional if self-hosting)

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
```

Configure your base `.env` file (acts as a fallback if in-game fields are left empty):

```env
OPENAI_API_BASE=https://api.groq.com/openai/v1
OPENAI_API_KEY=YOUR_KEY
OPENAI_MODEL=llama-3.1-8b-instant
TTS_API_URL=http://localhost:5000/synthesize
```

Run the backend:

```bash
uvicorn main:app --reload --port 8000
```
*Note: Go to `http://localhost:8000/dashboard` in your browser to open the control panel!*

---

> *"He watered the crops again. As if routine could somehow fill the emptiness."*  
> — The Narrator
