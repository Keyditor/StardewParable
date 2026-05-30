import os
import json
import logging
import requests
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
import pygame
import io
import gradio as gr
from datetime import datetime

load_dotenv()

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurações via variáveis de ambiente
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
TTS_API_URL = os.getenv("TTS_API_URL", "http://localhost:5000/synthesize")
if not "localhost" in TTS_API_URL:
    TTS_API_URL += "/synthesize"
    
app = FastAPI()

# Inicializa o mixer de áudio do pygame
pygame.mixer.init()

# Estado Global para o Dashboard e Histórico
global_actions_log = []
global_narrations_log = []

class ActionList(BaseModel):
    actions: List[str]
    openai_url: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    eleven_labs_api_key: Optional[str] = None
    eleven_labs_voice_id: Optional[str] = None

TURN_PROMPT = """Você é o narrador cínico e onisciente, inspirado no estilo de 'The Stanley Parable', observando um jogador em Stardew Valley.
Sua tarefa é ler a lista crua de ações de um TURNO do jogador e criar um ÚNICO RESUMO NARRATIVO de como foi esse período.

REGRAS CRÍTICAS (SIGA ESTRITAMENTE):
1. NUNCA repita ou cite as ações no formato de log (como '[08:10] Cortou Arvore' ou '[Keyd]'). Transforme as informações em uma história fluida.
2. Crie uma narrativa em formato de parágrafo(s) contando a rotina desse turno especificamente.
3. Seja extremamente sarcástico, irônico e julgue as decisões do jogador com desdém elegante. Questione a sanidade de regar plantas, cortar mato ou conversar com pessoas.
4. Mantenha a resposta com o máximo de 100 palavras.
5. Responda inteiramente em português do Brasil.
6. Você não é um robô lendo logs; você é uma entidade superior comentando sobre as atividades banais e questionáveis do protagonista.
7. Evite inventar eventos que não estão na lista; apenas embeleze e critique o que realmente aconteceu.

Contexto opcional do jogador:
- Ele é um streamer na Twitch e seu chat se chama 'Bapo'. Sinta-se à vontade para zombar que o 'Bapo' está assistindo essa perda de tempo, se achar oportuno."""

def load_prompt():
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts.json")
    with open(prompt_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    current_prompt_id = data["prompt_config"]["current_prompt_id"]
    system_prompt = data["prompt_config"]["prompts"][current_prompt_id]
    return system_prompt

def generate_narration(payload: ActionList, custom_prompt: str = None) -> str:
    system_prompt = custom_prompt if custom_prompt else load_prompt()
    
    # Prepara a lista de ações como string
    actions_text = "\n".join(f"- {action}" for action in payload.actions)
    
    # Adiciona histórico para continuidade (últimas 3 narrações para não estourar o limite de tokens)
    history_context = ""
    if global_narrations_log:
        recent_history = global_narrations_log[-3:]
        history_context = "\n\nHISTÓRICO DE NARRAÇÕES ANTERIORES (Para continuidade da história):\n" + "\n---\n".join([item["narration"] for item in recent_history])

    user_message = f"{history_context}\n\nAções recentes do jogador a serem narradas agora:\n{actions_text}"

    api_key = payload.openai_api_key if payload.openai_api_key else OPENAI_API_KEY
    api_url = payload.openai_url if payload.openai_url else OPENAI_API_BASE
    model = payload.openai_model if payload.openai_model else OPENAI_MODEL

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    request_payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    }

    logger.info(f"Enviando {len(payload.actions)} ações para a OpenAI em {api_url} com o modelo {model}...")
    response = requests.post(f"{api_url}/chat/completions", headers=headers, json=request_payload)
    
    if response.status_code != 200:
        logger.error(f"Erro na OpenAI: {response.text}")
        raise Exception(f"Erro na OpenAI: {response.status_code}")
        
    data = response.json()
    narration = data["choices"][0]["message"]["content"]
    logger.info(f"Narração gerada: {narration}")
    return narration

def synthesize_and_play(text: str, payload: ActionList):
    if payload.eleven_labs_api_key and payload.eleven_labs_voice_id:
        logger.info(f"Enviando texto para a API do ElevenLabs...")
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{payload.eleven_labs_voice_id}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": payload.eleven_labs_api_key
            }
            data = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5
                }
            }
            response = requests.post(url, json=data, headers=headers)
            if response.status_code != 200:
                logger.error(f"Erro no ElevenLabs: {response.text}")
                return
            audio_data = io.BytesIO(response.content)
            logger.info("Reproduzindo áudio do ElevenLabs...")
            pygame.mixer.music.load(audio_data)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            logger.info("Áudio finalizado.")
        except Exception as e:
            logger.error(f"Erro ElevenLabs: {e}")
    else:
        wav_path = os.path.join(os.path.dirname(__file__), "BraumS.wav")
        logger.info(f"Enviando texto para a API de TTS Local ({TTS_API_URL})...")
        try:
            with open(wav_path, "rb") as f:
                files = {
                    "speaker_wav": ("BraumS.wav", f, "audio/wav")
                }
                data = {
                    "text": text
                }
                
                response = requests.post(TTS_API_URL, files=files, data=data)
                
                if response.status_code != 200:
                    logger.error(f"Erro no TTS Local: {response.text}")
                    return
                
                audio_data = io.BytesIO(response.content)
                
                logger.info("Reproduzindo áudio do TTS Local...")
                pygame.mixer.music.load(audio_data)
                pygame.mixer.music.play()
                
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                    
                logger.info("Áudio finalizado.")
        except Exception as e:
            logger.error(f"Erro ao sintetizar e tocar áudio: {str(e)}")

def process_actions_task(payload: ActionList, custom_prompt: str = None):
    try:
        # Registrar ações recebidas
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        global_actions_log.append({
            "time": timestamp,
            "actions": payload.actions
        })
        
        narration = generate_narration(payload, custom_prompt)
        
        # Registrar narração gerada
        global_narrations_log.append({
            "time": timestamp,
            "narration": narration
        })
        
        synthesize_and_play(narration, payload)
    except Exception as e:
        logger.error(f"Erro no fluxo em background: {e}")

@app.post("/actions")
def receive_actions(action_list: ActionList, background_tasks: BackgroundTasks):
    logger.info(f"Recebidas {len(action_list.actions)} ações do mod.")
    background_tasks.add_task(process_actions_task, action_list)
    return {"message": "Ações recebidas e processamento iniciado em background"}

@app.post("/actionsturn")
def receive_actions_turn(action_list: ActionList, background_tasks: BackgroundTasks):
    logger.info(f"Recebidas {len(action_list.actions)} ações do mod (turno).")
    background_tasks.add_task(process_actions_task, action_list, TURN_PROMPT)
    return {"message": "Ações de turno recebidas e processamento iniciado em background"}

# ----------------- GRADIO DASHBOARD -----------------

def get_actions_display():
    if not global_actions_log:
        return "Nenhuma ação recebida ainda."
    display = ""
    for entry in reversed(global_actions_log):
        display += f"[{entry['time']}]\n"
        for act in entry['actions']:
            display += f"- {act}\n"
        display += "-"*40 + "\n"
    return display

def get_narrations_display():
    if not global_narrations_log:
        return "Nenhuma narração gerada ainda."
    display = ""
    for entry in reversed(global_narrations_log):
        display += f"[{entry['time']}]\n{entry['narration']}\n"
        display += "-"*40 + "\n"
    return display

def get_history_display():
    if not global_narrations_log:
        return "Nenhum histórico disponível para contexto."
    display = "Histórico das últimas 3 narrações enviadas como contexto:\n\n"
    for entry in global_narrations_log[-3:]:
        display += f"[{entry['time']}]\n{entry['narration']}\n\n"
    return display

def trigger_custom_narration(prompt: str, actions_text: str):
    actions_list = [a.strip() for a in actions_text.split('\n') if a.strip()]
    if not actions_list:
        return "Erro: Forneça pelo menos uma ação."
    if not prompt.strip():
        return "Erro: Forneça um prompt personalizado."
    
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        global_actions_log.append({
            "time": timestamp,
            "actions": actions_list
        })
        
        dummy_payload = ActionList(actions=actions_list)
        narration = generate_narration(dummy_payload, prompt)
        
        global_narrations_log.append({
            "time": timestamp,
            "narration": narration
        })
        
        synthesize_and_play(narration, dummy_payload)
        return f"Narração Gerada com Sucesso:\n\n{narration}"
    except Exception as e:
        return f"Erro ao gerar narração: {e}"

with gr.Blocks(title="Dashboard - ActionLogger") as dashboard:
    gr.Markdown("# Painel de Controle - Narrador Stardew Valley")
    
    with gr.Tabs():
        with gr.TabItem("Ações Recebidas"):
            actions_text_area = gr.Textbox(label="Log de Ações", lines=20, interactive=False)
            btn_refresh_actions = gr.Button("Atualizar Ações")
            btn_refresh_actions.click(fn=get_actions_display, inputs=[], outputs=[actions_text_area])
            
        with gr.TabItem("Narrações Geradas"):
            narrations_text_area = gr.Textbox(label="Log de Narrações", lines=20, interactive=False)
            btn_refresh_narrations = gr.Button("Atualizar Narrações")
            btn_refresh_narrations.click(fn=get_narrations_display, inputs=[], outputs=[narrations_text_area])
            
        with gr.TabItem("Contexto Histórico (Continuidade)"):
            gr.Markdown("Este é o histórico recente (últimas 3) injetado no prompt da IA para que ela se lembre dos eventos passados (Contexto).")
            history_text_area = gr.Textbox(label="Histórico Injetado", lines=15, interactive=False)
            btn_refresh_history = gr.Button("Atualizar Histórico")
            btn_refresh_history.click(fn=get_history_display, inputs=[], outputs=[history_text_area])
            
        with gr.TabItem("Gerar Narração Customizada"):
            gr.Markdown("Teste prompts customizados com ações simuladas (ou as últimas recebidas).")
            custom_prompt_input = gr.Textbox(label="Prompt Personalizado", lines=10, value=TURN_PROMPT)
            custom_actions_input = gr.Textbox(label="Ações (uma por linha)", lines=5, placeholder="[08:00] [Jogador] [Fazenda] Cortou Árvore\n[09:00] [Jogador] [Fazenda] Regou Planta")
            btn_generate = gr.Button("Gerar e Tocar")
            custom_output = gr.Textbox(label="Resultado", lines=10, interactive=False)
            
            btn_generate.click(fn=trigger_custom_narration, inputs=[custom_prompt_input, custom_actions_input], outputs=[custom_output])

# Monta o Gradio na rota /dashboard do FastAPI
app = gr.mount_gradio_app(app, dashboard, path="/dashboard")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)