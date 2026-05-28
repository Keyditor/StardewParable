# 🌾 StardewParable 🎙️

**Criado por Keyditor**

*"Esta é a história de um fazendeiro chamado..."* 

**StardewParable** é um mod para Stardew Valley fortemente inspirado na narrativa de *The Stanley Parable*. Ele observa silenciosamente todas as suas ações, escolhas e o seu trabalho (frequentemente questionável) na fazenda e na Vila Pelicanos. Ao final de cada dia, um narrador onisciente, sarcástico e cínico usa inteligência artificial para resumir a sua rotina diária em formato de narração por voz!

## ✨ Funcionalidades

- 📜 **Rastreamento de Ações:** O mod registra de forma invisível as suas atividades diárias, incluindo uso de ferramentas (regar, arar, cortar lenha, minerar, pescar), transições de cenários, interações com NPCs, criação de itens (crafting) e visualização de cutscenes.
- 🤖 **Integração com LLM:** Suas ações são enviadas para um backend em Python que utiliza a API da OpenAI (ou Groq/compatíveis) para redigir um parágrafo narrativo único e fluído, cheio de ironia e desdém elegante sobre as suas decisões.
- 🗣️ **Síntese de Voz (TTS):** A história gerada é enviada para uma API de Text-to-Speech (TTS) e reproduzida em áudio instantaneamente, permitindo que você ouça a narração do seu dia enquanto a tela de lucros é exibida.

## 🛠️ Arquitetura do Projeto

O projeto é dividido em três partes principais:
1. **Mod SMAPI (C#):** Responsável por capturar os eventos do Stardew Valley em tempo real e enviar um pacote (JSON) com as ações do dia ao final da noite.
2. **Backend Python (FastAPI):** Recebe as ações do mod, constrói o prompt (configurado em `prompts.json`), envia ao modelo de linguagem (LLM) para gerar a história e repassa o texto final para o serviço de voz.
3. **Servidor TTS (Flask/Ngrok):** Uma API externa (como um Google Colab) que recebe o texto e um arquivo de voz base (`BraumS.wav`) e devolve o áudio sintetizado para ser reproduzido pela biblioteca `pygame` do backend Python.

## 🚀 Como Instalar e Executar

### 1. Pré-requisitos
- [SMAPI](https://smapi.io/) instalado no seu Stardew Valley.
- [Python 3.8+](https://www.python.org/) instalado no seu computador.
- Um servidor de Text-to-Speech (TTS) rodando (por exemplo, via XTTS/Colab).
- Uma chave de API de LLM (OpenAI, Groq, etc.).

### 2. Configurando o Mod
1. Compile o projeto C# ou copie a pasta gerada `ActionLogger` de dentro de `bin/Debug/net6.0/` para a pasta `Mods` do seu Stardew Valley.
2. Inicie o jogo pelo SMAPI.

### 3. Configurando o Backend Python
1. Navegue até a pasta `backend/`.
2. Instale as dependências executando:
   ```bash
   pip install -r requirements.txt
   ```
3. Renomeie o arquivo ou edite o `.env` na pasta `backend` com as suas credenciais:
   ```env
   OPENAI_API_BASE=https://api.groq.com/openai/v1
   OPENAI_API_KEY=sua_chave_aqui
   OPENAI_MODEL=llama-3.1-8b-instant
   TTS_API_URL=https://sua-url-do-ngrok.ngrok-free.app/synthesize
   ```
4. Inicie o servidor FastAPI:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

### 4. Jogando
Jogue normalmente! Vá dormir no final do dia. O mod irá compilar suas atividades, enviar ao backend, e você ouvirá o narrador comentando sobre suas decisões de vida.

---
*"Ele regou as plantações... De novo. Como se isso fosse preencher o vazio em seu coração."* - O Narrador.