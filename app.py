from flask import Flask, request, jsonify, send_file, render_template_string
from flask_cors import CORS
import openai
import tempfile
import os
import json
import csv
from datetime import datetime

app = Flask(__name__)
CORS(app)

openai.api_key = os.environ.get("OPENAI_API_KEY")
allowed_passwords = os.environ.get("ALLOWED_PASSWORDS", "").split(",")
admin_password = os.environ.get("ADMIN_PASSWORD", "")

LOG_JSON = "logs.json"
LOG_CSV = "logs.csv"

if not os.path.exists(LOG_JSON):
    with open(LOG_JSON, "w") as f:
        json.dump([], f)
if not os.path.exists(LOG_CSV):
    with open(LOG_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["user", "filename", "format", "timestamp", "status"])

@app.route("/verify-password", methods=["POST"])
def verify_password():
    pw = request.form.get("password")
    if pw in allowed_passwords:
        return "OK", 200
    return "Unauthorized", 401

@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file uploaded."}), 400

    user_password = request.form.get("password")
    if user_password not in allowed_passwords:
        return jsonify({"error": "Unauthorized"}), 401

    output_format = request.form.get("format", "txt")
    audio_file = request.files["audio"]
    filename = audio_file.filename or "uploaded_audio"

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        audio_path = tmp.name
        audio_file.save(audio_path)

    status = "success"
    try:
        transcript = openai.Audio.transcribe(
            model="whisper-1",
            file=open(audio_path, "rb"),
            response_format="text" if output_format == "txt" else "srt",
            language="zh"
        )

        log_entry = {
            "user": user_password,
            "filename": filename,
            "format": output_format,
            "timestamp": datetime.utcnow().isoformat(),
            "status": status
        }
        append_log(log_entry)

        if output_format == "txt":
            return jsonify({"text": transcript})
        else:
            srt_path = audio_path + ".srt"
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(transcript)
            return send_file(srt_path, as_attachment=True)

    except Exception as e:
        status = str(e)
        append_log({
            "user": user_password,
            "filename": filename,
            "format": output_format,
            "timestamp": datetime.utcnow().isoformat(),
            "status": status
        })
        return jsonify({"error": status}), 500
    finally:
        os.remove(audio_path)
        if os.path.exists(audio_path + ".srt"):
            os.remove(audio_path + ".srt")

@app.route("/admin-auth", methods=["POST"])
def admin_auth():
    pw = request.form.get("password")
    if pw != admin_password:
        return "Unauthorized", 401

    with open(LOG_JSON, "r", encoding="utf-8") as f:
        logs = json.load(f)

    table = "".join([
        f"<tr><td>{log['user']}</td><td>{log['filename']}</td><td>{log['format']}</td><td>{log['timestamp']}</td><td>{log['status']}</td></tr>"
        for log in logs
    ])

    return render_template_string(f"""
    <html>
    <head>
        <title>管理介面</title>
        <style>
            body {{ font-family: sans-serif; padding: 2rem; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
        </style>
    </head>
    <body>
        <h2>使用紀錄</h2>
        <table>
            <tr><th>使用者</th><th>檔案</th><th>格式</th><th>時間</th><th>狀態</th></tr>
            {table}
        </table>
        <br>
        <form method="GET" action="/download-csv">
            <input type="hidden" name="auth" value="{pw}" />
            <button type="submit">下載 CSV</button>
        </form>
    </body>
    </html>
    """)

@app.route("/download-csv")
def download_csv():
    auth = request.args.get("auth")
    if auth != admin_password:
        return "Unauthorized", 401
    return send_file(LOG_CSV, as_attachment=True)

@app.route("/")
def index():
    return "Whisper Transcriber API is running."

def append_log(entry):
    with open(LOG_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.append(entry)
    with open(LOG_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    with open(LOG_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([entry["user"], entry["filename"], entry["format"], entry["timestamp"], entry["status"]])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
