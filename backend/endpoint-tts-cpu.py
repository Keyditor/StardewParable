from flask import Flask, request, send_file, jsonify
from pyngrok import ngrok
import os
from werkzeug.utils import secure_filename
from pocket_tts import TTSModel
import scipy.io.wavfile
import threading
from tqdm import tqdm
import hashlib

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# Garante que a pasta para os uploads existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

print("Carregando modelo pocket-tts portuguese_24l...")
tts_model = TTSModel.load_model(language="portuguese_24l")

voice_state_cache = {}

@app.route('/synthesize', methods=['POST'])
def synthesize():
    try:
        # Obter texto e validar entrada
        text = request.form.get('text')
        if not text:
            return jsonify({"error": "Texto é obrigatório."}), 400

        # Salvar o arquivo de voz enviado (speaker_wav)
        speaker_wav = request.files.get('speaker_wav')
        if not speaker_wav:
            return jsonify({"error": "O arquivo speaker_wav é obrigatório."}), 400

        speaker_wav_filename = secure_filename(speaker_wav.filename)
        speaker_wav_path = os.path.join(app.config['UPLOAD_FOLDER'], speaker_wav_filename)
        speaker_wav.save(speaker_wav_path)

        print(f"[DEBUG] Recebido texto para síntese: '{text}'")
        print(f"[DEBUG] Arquivo de áudio de referência salvo em: {speaker_wav_path}")

        # Calcula o hash do arquivo de áudio para usar como chave de cache
        with open(speaker_wav_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()

        # Gerar o áudio usando o arquivo enviado
        output_file = 'output.wav'
        
        if file_hash in voice_state_cache:
            print("[DEBUG] Áudio de referência idêntico detectado! Usando voz guardada na memória para agilizar...")
            voice_state = voice_state_cache[file_hash]
        else:
            print("[DEBUG] Processando nova referência de áudio e extraindo características...")
            voice_state = tts_model.get_state_for_audio_prompt(speaker_wav_path)
            voice_state_cache[file_hash] = voice_state
            
        print("[DEBUG] Gerando áudio da fala...")
        
        # Container para capturar o resultado da Thread
        audio_result = []
        
        def process_audio():
            audio_tensor = tts_model.generate_audio(voice_state, text, frames_after_eos=4)
            audio_result.append(audio_tensor)
            
        thread = threading.Thread(target=process_audio)
        thread.start()
        
        # Estimativa de tempo: ~0.05 segundos por caractere na CPU (ajustável de acordo com seu PC)
        estimated_time = max(len(text) * 0.05, 1.0)
        steps = 100
        step_time = estimated_time / steps
        
        with tqdm(total=steps, desc="Síntese TTS") as pbar:
            while thread.is_alive():
                thread.join(timeout=step_time)
                if not thread.is_alive():
                    pbar.update(steps - pbar.n) # Completa a barra subitamente ao terminar
                    break
                if pbar.n < 99:
                    pbar.update(1)
                    
        audio = audio_result[0]
        scipy.io.wavfile.write(output_file, tts_model.sample_rate, audio.cpu().numpy())

        print(f"[DEBUG] Áudio gerado com sucesso e salvo em: {output_file}")
        return send_file(output_file, as_attachment=True)

    except Exception as e:
        print(f"[ERRO] Falha ao sintetizar áudio: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Inicia o servidor Flask com ngrok
if __name__ == '__main__':
    # Cria o túnel ngrok
    public_url = ngrok.connect(5000).public_url
    print(f"Servidor público do ngrok rodando em: {public_url}")

    # Inicia o servidor Flask
    app.run(host='0.0.0.0', port=5000)