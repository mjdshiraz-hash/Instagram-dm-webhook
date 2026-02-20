import os
import requests
from flask import Flask, request

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "change-me")

TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TG_THREAD_ID = os.getenv("TELEGRAM_THREAD_ID", "")  # optional


def send_to_telegram(text: str) -> None:
    if not TG_TOKEN or not TG_CHAT_ID:
        print("Telegram not configured: missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
        return

    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "disable_web_page_preview": True,
    }
    if TG_THREAD_ID:
        payload["message_thread_id"] = int(TG_THREAD_ID)

    try:
        r = requests.post(url, json=payload, timeout=10)
        print("Telegram sendMessage status:", r.status_code, r.text[:300])
    except Exception as e:
        print("Telegram sendMessage error:", repr(e))


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
    print("WEBHOOK EVENT:", data)

    # تلاش برای استخراج متن پیام‌های دایرکت
    try:
        entries = data.get("entry", [])
        for entry in entries:
            messaging = entry.get("messaging", [])
            for m in messaging:
                msg = m.get("message", {}) or {}
                text = msg.get("text")
                if text:
                    sender = (m.get("sender", {}) or {}).get("id", "unknown")
                    mid = msg.get("mid", "")
                    out = f"📩 Instagram DM\nFrom: {sender}\nMID: {mid}\nText: {text}"
                    send_to_telegram(out)
    except Exception as e:
        print("Parse error:", repr(e))

    return "OK", 200


@app.get("/")
def health():
    return "OK", 200
