from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import openai
import tempfile
import os

app = Flask(__name__)
CORS(app)  # 啟用 CORS，允許跨網域存取

# 從 Render 的環境變數讀取 OpenAI API 金鑰與 App 密碼
openai.api_key = os.environ.get("OPENAI_API_KEY")
app_password = os.environ.get("APP_PASSWORD", "")

@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file uploaded."}), 400

    password = request.form.get("password")
    if password != app_password:
        return jsonify({"error": "Unauthorized"}), 401

    output_format = request.form.get("format", "txt")
    audio_file = request.files["audio"]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        audio_path = tmp.name
        audio_file.save(audio_path)

    try:
        transcript = openai.Audio.transcribe(
            model="whisper-1",
            file=open(audio_path, "rb"),
            response_format="text" if output_format == "txt" else "srt",
            language="zh"
        )

        if output_format == "txt":
            return jsonify({"text": transcript})
        else:
            srt_path = audio_path + ".srt"
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(transcript)
            return send_file(srt_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        os.remove(audio_path)
        if os.path.exists(audio_path + ".srt"):
            os.remove(audio_path + ".srt")

@app.route("/")
def index():
    return "Whisper Transcriber API is running."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
