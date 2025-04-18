from flask import Flask, request, jsonify, send_file
import openai
import tempfile
import os

app = Flask(__name__)

# 從 Render 的環境變數讀取 OpenAI API 金鑰
openai.api_key = os.environ.get("OPENAI_API_KEY")

@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file uploaded."}), 400

    output_format = request.form.get("format", "txt")  # 預設為 txt
    audio_file = request.files["audio"]

    # 將上傳音檔存為暫存檔
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        audio_path = tmp.name
        audio_file.save(audio_path)

    try:
        # 呼叫 OpenAI Whisper API
        transcript = openai.Audio.transcribe(
            model="whisper-1",
            file=open(audio_path, "rb"),
            response_format="text" if output_format == "txt" else "srt",
            language="zh"  # 中文為主（可辨識中英混合）
        )

        # 如果是 txt 直接回傳 JSON
        if output_format == "txt":
            return jsonify({"text": transcript})
        else:
            # 如果是 srt，先儲存成檔案再回傳
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
