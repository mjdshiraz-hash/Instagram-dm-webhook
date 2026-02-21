import os
import requests
from flask import Flask, request

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "change-me")

TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TG_THREAD_ID = os.getenv("TELEGRAM_THREAD_ID", "")  # optional

# ---------------------------
# 1) Rule Engine (Model A)
# ---------------------------

BAD_WORDS = [
    "کص", "کیر", "fuck", "sex", "تبلیغ", "پولدارشو", "جاوید شاه", "شاهزاده", "منافق", "منافقین", "سه فاسد", "جانم فدای رهبری", "شرط بندی"
]
TEAM_WORDS = [
    "همکاری", "ادمین", "مدیریت", "تیم", "ارتباط", "تماس", "همکار", "پشتیبانی"
]
NEWS_WORDS = [
    "خبر", "گزارش", "فوری", "ویدیو", "فیلم", "عکس", "سند", "مدرک"
]


def classify(text: str) -> str:
    """Return one of: general, team, news, links, spam, long"""
    if not text:
        return "general"

    t = text.strip().lower()

    # links
    if "http://" in t or "https://" in t or "t.me/" in t or "instagram.com/" in t:
        return "links"

    # spam / abuse
    if any(w in t for w in BAD_WORDS):
        return "spam"

    # team / collaboration
    if any(w in t for w in TEAM_WORDS):
        return "team"

    # news / reports
    if any(w in t for w in NEWS_WORDS):
        return "news"

    # long messages
    if len(t) > 300:
        return "long"

    return "general"


def build_message(category: str, sender_id: str, text: str) -> str:
    """
    Option 1 format (short + category):
    #links | (id:123)
    message text...
    """
    sender = sender_id or "unknown"
    return f"#{category} | (id:{sender})\n{text}".strip()


# ---------------------------
# 2) Telegram sender
# ---------------------------

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
        # Topic support (optional)
        try:
            payload["message_thread_id"] = int(TG_THREAD_ID)
        except ValueError:
            print("Invalid TELEGRAM_THREAD_ID; must be an integer.")

    try:
        r = requests.post(url, json=payload, timeout=10)
        print("Telegram sendMessage status:", r.status_code, r.text[:300])
    except Exception as e:
        print("Telegram sendMessage error:", repr(e))


# ---------------------------
# 3) Webhook endpoints
# ---------------------------

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

    # لاگ امن: فقط کلیدها + تعداد entry
    try:
        entries = data.get("entry", []) or []
        print("WEBHOOK: keys=", list(data.keys()), "entries=", len(entries))
    except Exception:
        print("WEBHOOK: received event")

    # استخراج پیام‌ها
    try:
        entries = data.get("entry", []) or []
        for entry in entries:
            messaging = entry.get("messaging", []) or []
            for m in messaging:
                msg = m.get("message", {}) or {}
                text = msg.get("text", "")

                # فقط پیام‌های متنی را فعلاً جلو می‌بریم
                if not text:
                    continue

                sender_id = (m.get("sender", {}) or {}).get("id", "unknown")

                category = classify(text)
                out = build_message(category, sender_id, text)

                send_to_telegram(out)

    except Exception as e:
        print("Parse error:", repr(e))

    return "OK", 200


@app.get("/")
def health():
    return "OK", 200
