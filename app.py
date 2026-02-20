import os
from flask import Flask, request

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "change-me")

@app.get("/webhook")
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403

@app.post("/webhook")
def webhook():
    data = request.get_json(silent=True) or {}
    # فعلاً فقط لاگ می‌کنیم تا مطمئن شویم وبهوک می‌رسد
    print("WEBHOOK EVENT:", data)
    return "OK", 200

@app.get("/")
def health():
    return "OK", 200
