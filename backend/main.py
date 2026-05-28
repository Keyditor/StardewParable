import os
import json
import logging
import requests
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv
import pygame
import io

load_dotenv()

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurações via variáveis de ambiente
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
TTS_API_URL = os.getenv("TTS_API_URL", "http://localhost:5000/synthesize")

app = FastAPI()

# Inicializa o mixer de áudio do pygame
pygame.mixer.init()

class ActionList(BaseModel):
    actions: List[str]

def load_prompt():
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts.json")
    with open(prompt_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    current_prompt_id = data["prompt_config"]["current_prompt_id"]
    system_prompt = data["prompt_config"]["prompts"][current_prompt_id]
    return system_prompt

def generate_narration(actions: List[str]) -> str:
    system_prompt = load_prompt()
    
    # Prepara a lista de ações como string
    actions_text = "\n".join(f"- {action}" for action in actions)
    user_message = f"Ações do jogador:\n{actions_text}"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    }

    logger.info(f"Enviando {len(actions)} ações para a OpenAI...")
    response = requests.post(f"{OPENAI_API_BASE}/chat/completions", headers=headers, json=payload)
    
    if response.status_code != 200:
        logger.error(f"Erro na OpenAI: {response.text}")
        raise Exception(f"Erro na OpenAI: {response.status_code}")
        
    data = response.json()
    narration = data["choices"][0]["message"]["content"]
    logger.info(f"Narração gerada: {narration}")
    return narration

def synthesize_and_play(text: str):
    wav_path = os.path.join(os.path.dirname(__file__), "BraumS.wav")
    
    logger.info(f"Enviando texto para a API de TTS ({TTS_API_URL})...")
    
    try:
        with open(wav_path, "rb") as f:
            # Enviamos o arquivo .wav na chave 'speaker_wav' e o texto.
            files = {
                "speaker_wav": ("BraumS.wav", f, "audio/wav")
            }
            data = {
                "text": text
            }
            
            response = requests.post(TTS_API_URL, files=files, data=data)
            
            if response.status_code != 200:
                logger.error(f"Erro no TTS: {response.text}")
                return
            
            audio_data = io.BytesIO(response.content)
            
            logger.info("Reproduzindo áudio...")
            pygame.mixer.music.load(audio_data)
            pygame.mixer.music.play()
            
            # Aguarda terminar de tocar
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
                
            logger.info("Áudio finalizado.")
    except Exception as e:
        logger.error(f"Erro ao sintetizar e tocar áudio: {str(e)}")

def process_actions_task(actions: List[str]):
    try:
        narration = generate_narration(actions)
        synthesize_and_play(narration)
    except Exception as e:
        logger.error(f"Erro no fluxo em background: {e}")

@app.post("/actions")
def receive_actions(action_list: ActionList, background_tasks: BackgroundTasks):
    logger.info(f"Recebidas {len(action_list.actions)} ações do mod.")
    background_tasks.add_task(process_actions_task, action_list.actions)
    return {"message": "Ações recebidas e processamento iniciado em background"}
