from flask import Flask, request, send_file, jsonify
from pyngrok import ngrok
import os
from werkzeug.utils import secure_filename
from pocket_tts import TTSModel
import scipy.io.wavfile

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# Garante que a pasta para os uploads existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

print("Carregando modelo pocket-tts portuguese_24l...")
tts_model = TTSModel.load_model(language="portuguese_24l")

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
        
        voice_state = tts_model.get_state_for_audio_prompt(speaker_wav_path)
        audio = tts_model.generate_audio(voice_state, text, frames_after_eos=4)
        scipy.io.wavfile.write(output_file, tts_model.sample_rate, audio.cpu().numpy())

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