from flask import Flask, request, send_file, jsonify
from pyngrok import ngrok
import os
from werkzeug.utils import secure_filename
from TTS.api import TTS
import torch

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Usando dispositivo: {device}")

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# Garante que a pasta para os uploads existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=True).to(device)
#tts.model = tts.model.to(device)

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

        # Gerar o áudio usando o arquivo enviado
        output_file = 'output.wav'
        tts.tts_to_file(text=text, file_path=output_file, speaker_wav=speaker_wav_path, language="pt")

        return send_file(output_file, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Inicia o servidor Flask com ngrok
if __name__ == '__main__':
    # Cria o túnel ngrok
    public_url = ngrok.connect(5000).public_url
    print(f"Servidor público do ngrok rodando em: {public_url}")

    # Inicia o servidor Flask
    app.run(host='0.0.0.0', port=5000)