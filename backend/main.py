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
class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[94m',
        'INFO': '\033[92m',      # Verde
        'WARNING': '\033[93m',   # Amarelo
        'ERROR': '\033[91m',     # Vermelho
        'CRITICAL': '\033[95m'   # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        time_str = self.formatTime(record, "%d/%m %H:%M:%S")
        return f"\033[90m[{time_str}]\033[0m {color}{record.levelname:8}\033[0m | {record.getMessage()}"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter())
logger.addHandler(handler)
logger.propagate = False

# Configurações via variáveis de ambiente
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
TTS_API_URL = os.getenv("TTS_API_URL", "http://localhost:5000/synthesize")
if not "localhost" in TTS_API_URL and not TTS_API_URL.endswith("/synthesize"):
    TTS_API_URL += "/synthesize"
ELEVEN_LABS_API_KEY = os.getenv("ELEVEN_LABS_API_KEY", "")
ELEVEN_LABS_VOICE_ID = os.getenv("ELEVEN_LABS_VOICE_ID", "")
    
app = FastAPI()

# Inicializa o mixer de áudio do pygame
pygame.mixer.init()

# Estado Global para o Dashboard e Histórico
global_actions_log = []
global_narrations_log = []
last_known_config = {}

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

def check_config_changes(payload: ActionList):
    global last_known_config
    
    def mask_key(k):
        if not k: return None
        return f"{k[:4]}...{k[-4:]}" if len(k) > 8 else "***"

    current_config = {
        "URL da OpenAI": payload.openai_url,
        "Modelo da IA": payload.openai_model,
        "Chave da OpenAI": mask_key(payload.openai_api_key),
        "Chave do ElevenLabs": mask_key(payload.eleven_labs_api_key),
        "Voz do ElevenLabs": payload.eleven_labs_voice_id,
    }
    
    changes = []
    if not last_known_config:
        last_known_config = current_config
        return

    for key, value in current_config.items():
        old_value = last_known_config.get(key)
        if value != old_value and value is not None:
            if old_value is None:
                changes.append(f"{key}: Definido como \033[1m'{value}'\033[0m")
            else:
                changes.append(f"{key}: \033[31m'{old_value}'\033[0m -> \033[32m'{value}'\033[0m")
                
    if changes:
        logger.info("\033[93m[⚙️ CONFIGURAÇÕES ATUALIZADAS PELO JOGO]\033[0m")
        for change in changes:
            logger.info(f"   \033[96m↳ {change}\033[0m")
            
    last_known_config = current_config

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

    logger.info(f"🚀 Enviando \033[1m{len(payload.actions)}\033[0m ações para a IA ({model})...")
    response = requests.post(f"{api_url}/chat/completions", headers=headers, json=request_payload)
    
    if response.status_code != 200:
        logger.error(f"Erro na OpenAI: {response.text}")
        raise Exception(f"Erro na OpenAI: {response.status_code}")
        
    data = response.json()
    narration = data["choices"][0]["message"]["content"]
    logger.info(f"🧠 Narração gerada:\n\033[3m{narration}\033[0m")
    return narration

def synthesize_and_play(text: str, payload: ActionList):
    el_key = payload.eleven_labs_api_key if payload.eleven_labs_api_key else ELEVEN_LABS_API_KEY
    el_voice = payload.eleven_labs_voice_id if payload.eleven_labs_voice_id else ELEVEN_LABS_VOICE_ID
    
    if el_key and el_voice:
        logger.info(f"🎙️ Enviando texto para a API do ElevenLabs...")
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{el_voice}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": el_key
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
            logger.info("▶️ Reproduzindo áudio do ElevenLabs...")
            pygame.mixer.music.load(audio_data)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            logger.info("✅ Áudio finalizado.")
        except Exception as e:
            logger.error(f"Erro ElevenLabs: {e}")
    else:
        wav_path = os.path.join(os.path.dirname(__file__), "BraumS.wav")
        logger.info(f"🎙️ Enviando texto para a API de TTS Local ({TTS_API_URL})...")
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
                
                logger.info("▶️ Reproduzindo áudio do TTS Local...")
                pygame.mixer.music.load(audio_data)
                pygame.mixer.music.play()
                
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                    
                logger.info("✅ Áudio finalizado.")
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
    check_config_changes(action_list)
    logger.info(f"📦 Recebidas \033[1m{len(action_list.actions)}\033[0m ações do mod (Fim do dia).")
    background_tasks.add_task(process_actions_task, action_list)
    return {"message": "Ações recebidas e processamento iniciado em background"}

@app.post("/actionsturn")
def receive_actions_turn(action_list: ActionList, background_tasks: BackgroundTasks):
    check_config_changes(action_list)
    logger.info(f"📦 Recebidas \033[1m{len(action_list.actions)}\033[0m ações do mod (Turno).")
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

def save_settings(new_openai_base, new_openai_key, new_openai_model, new_tts_url, new_el_key, new_el_voice):
    global OPENAI_API_BASE, OPENAI_API_KEY, OPENAI_MODEL, TTS_API_URL, ELEVEN_LABS_API_KEY, ELEVEN_LABS_VOICE_ID
    OPENAI_API_BASE = new_openai_base
    OPENAI_API_KEY = new_openai_key
    OPENAI_MODEL = new_openai_model
    TTS_API_URL = new_tts_url
    ELEVEN_LABS_API_KEY = new_el_key
    ELEVEN_LABS_VOICE_ID = new_el_voice
    logger.info("\033[93m[⚙️ CONFIGURAÇÕES ATUALIZADAS PELO DASHBOARD]\033[0m")
    return f"Configurações salvas com sucesso em {datetime.now().strftime('%H:%M:%S')}!"

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
            
        with gr.TabItem("Configurações Globais"):
            gr.Markdown("Altere as APIs, URLs e modelos utilizados como padrão (caso o Mod não envie valores específicos do jogo). As mudanças feitas aqui passam a valer imediatamente no backend.")
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### Inteligência Artificial (Texto)")
                    in_openai_base = gr.Textbox(label="URL Base da API", value=OPENAI_API_BASE, placeholder="Ex: https://api.groq.com/openai/v1")
                    in_openai_key = gr.Textbox(label="Chave da API (OpenAI/Groq/etc)", value=OPENAI_API_KEY, type="password")
                    in_openai_model = gr.Textbox(label="Modelo da IA", value=OPENAI_MODEL, placeholder="Ex: llama-3.1-8b-instant")
                with gr.Column():
                    gr.Markdown("### Síntese de Voz (TTS)")
                    in_tts_url = gr.Textbox(label="URL do TTS Local", value=TTS_API_URL, placeholder="Ex: http://localhost:5000/synthesize")
                    in_el_key = gr.Textbox(label="Chave do ElevenLabs (Opcional)", value=ELEVEN_LABS_API_KEY, type="password")
                    in_el_voice = gr.Textbox(label="ID da Voz do ElevenLabs (Opcional)", value=ELEVEN_LABS_VOICE_ID)
            
            btn_save_config = gr.Button("Salvar Configurações", variant="primary")
            config_status = gr.Textbox(label="Status", interactive=False)
            
            btn_save_config.click(
                fn=save_settings,
                inputs=[in_openai_base, in_openai_key, in_openai_model, in_tts_url, in_el_key, in_el_voice],
                outputs=[config_status]
            )

# Monta o Gradio na rota /dashboard do FastAPI
app = gr.mount_gradio_app(app, dashboard, path="/dashboard")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)