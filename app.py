import os
import requests
from flask import Flask, request

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "change-me")

TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TG_THREAD_ID = os.getenv("TELEGRAM_THREAD_ID", "")  # optional

# ---- NEW: Meta + IG page settings
# اگر ENV تو اسم دیگری دارد، من چند تا نام را هم چک می‌کنم:
META_ACCESS_TOKEN = (
    os.getenv("META_ACCESS_TOKEN", "")
    or os.getenv("META_TOKEN", "")
    or os.getenv("FACEBOOK_ACCESS_TOKEN", "")
    or os.getenv("GRAPH_API_TOKEN", "")
)

IG_PAGE_URL = os.getenv("IG_PAGE_URL", "https://www.instagram.com/iranazadinews/")

# ---- NEW: simple in-memory cache for usernames
USERNAME_CACHE = {}


# ---------------------------
# 1) Rule Engine (Model A)
# ---------------------------

BAD_WORDS = [
    "کص", "کیر", "fuck", "sex", "تبلیغ", "شرط بندی", "casino", "bet"
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


# ---------------------------
# 2) Username lookup (Graph API)
# ---------------------------

def get_username_from_graph(sender_id: str):
    """
    Try to resolve sender_id to Instagram username via Graph API.
    Returns string username without '@' OR None if not available.
    """
    if not META_ACCESS_TOKEN or not sender_id or sender_id == "unknown":
        return None

    if sender_id in USERNAME_CACHE:
        return USERNAME_CACHE[sender_id]

    try:
        url = f"https://graph.facebook.com/v21.0/{sender_id}"
        r = requests.get(
            url,
            params={"fields": "username", "access_token": META_ACCESS_TOKEN},
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            username = data.get("username")
            if username:
                USERNAME_CACHE[sender_id] = username
                return username
        else:
            # برای دیباگ سبک (بدون لو رفتن توکن)
            print("username lookup non-200:", r.status_code, (r.text or "")[:200])
    except Exception as e:
        print("username lookup error:", repr(e))

    return None


# ---------------------------
# 3) Telegram formatting + sender
# ---------------------------

def build_message(category: str, username, sender_id: str, text: str) -> str:
    # Option 1 + category + clickable page link
    who = f"@{username}" if username else f"(id:{sender_id or 'unknown'})"
    return f"#{category} | {who} | {IG_PAGE_URL}\n{text}".strip()


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
# 4) Webhook endpoints
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

    # log safe summary
    entries = data.get("entry", []) or []
    print("WEBHOOK: keys=", list(data.keys()), "entries=", len(entries))

    try:
        for entry in entries:
            messaging = entry.get("messaging", []) or []
            for m in messaging:
                msg = m.get("message", {}) or {}
                text = msg.get("text", "")

                # Only text messages for now
                if not text:
                    continue

                sender_id = (m.get("sender", {}) or {}).get("id", "unknown")

                category = classify(text)

                # NEW: try to get @username
                username = get_username_from_graph(sender_id)

                out = build_message(category, username, sender_id, text)
                send_to_telegram(out)

    except Exception as e:
        print("Parse error:", repr(e))

    return "OK", 200


@app.get("/")
def health():
    return "OK", 200
