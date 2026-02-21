import os
import requests
from flask import Flask, request

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "change-me")

TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TG_THREAD_ID = os.getenv("TELEGRAM_THREAD_ID", "")  # optional

META_ACCESS_TOKEN = os.getenv("IG_TOKEN", "").strip().replace("Bearer ", "")

USERNAME_CACHE = {}
TOKEN_CHECKED = False
TOKEN_OK = False

BAD_WORDS = [
    "کص", "کیر", "fuck", "sex", "تبلیغ", "پولدارشو", "جاوید شاه", "شاهزاده",
    "منافق", "منافقین", "سه فاسد", "جانم فدای رهبری", "شرط بندی"
]
TEAM_WORDS = ["همکاری", "ادمین", "مدیریت", "تیم", "ارتباط", "تماس"]
NEWS_WORDS = ["خبر", "گزارش", "فوری", "ویدیو", "فیلم", "عکس", "سند"]


def classify(text: str) -> str:
    if not text:
        return "general"
    t = text.lower()
    if "http" in t or "t.me/" in t or "instagram.com/" in t:
        return "links"
    if any(w in t for w in BAD_WORDS):
        return "spam"
    if any(w in t for w in TEAM_WORDS):
        return "team"
    if any(w in t for w in NEWS_WORDS):
        return "news"
    if len(t) > 300:
        return "long"
    return "general"


def check_token_once():
    global TOKEN_CHECKED, TOKEN_OK
    if TOKEN_CHECKED:
        return TOKEN_OK
    TOKEN_CHECKED = True

    if not META_ACCESS_TOKEN:
        print("META TOKEN MISSING: IG_TOKEN is empty")
        TOKEN_OK = False
        return TOKEN_OK

    safe_preview = f"{META_ACCESS_TOKEN[:6]}...{META_ACCESS_TOKEN[-6:]}"
    print("META TOKEN preview (safe):", safe_preview, "len=", len(META_ACCESS_TOKEN))

    try:
        # فقط برای تایید توکن — اگر این endpoint با توکن شما سازگار نبود، باز هم سیستم webhook خراب نمی‌شود
        url = "https://graph.facebook.com/v25.0/me"
        r = requests.get(url, params={"access_token": META_ACCESS_TOKEN}, timeout=10)
        if r.status_code == 200:
            TOKEN_OK = True
            print("META TOKEN OK")
            return TOKEN_OK

        print("META TOKEN CHECK non-200:", r.status_code, (r.text or "")[:300])
        TOKEN_OK = True  # اجازه می‌دهیم lookup بعدی تلاش کند
        return TOKEN_OK

    except Exception as e:
        print("META TOKEN CHECK ERROR:", repr(e))
        TOKEN_OK = True  # باز هم اجازه می‌دهیم lookup تلاش کند
        return TOKEN_OK


def get_username_from_graph(sender_id: str):
    if not sender_id or sender_id == "unknown":
        return None

    check_token_once()

    if sender_id in USERNAME_CACHE:
        return USERNAME_CACHE[sender_id]

    try:
        url = f"https://graph.facebook.com/v25.0/{sender_id}"
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

        print("username lookup failed:", r.status_code, (r.text or "")[:300])

    except Exception as e:
        print("username lookup error:", repr(e))

    return None


def build_message(category: str, username, sender_id: str, text: str):
    who = f"@{username}" if username else f"(id:{sender_id})"

    # ✅ لینک فقط وقتی username داریم (تا گمراه‌کننده نباشد)
    if username:
        link = f"https://www.instagram.com/{username}/"
        return f"#{category} | {who} | {link}\n{text}".strip()

    return f"#{category} | {who}\n{text}".strip()


def send_to_telegram(text: str) -> None:
    if not TG_TOKEN or not TG_CHAT_ID:
        print("Telegram not configured")
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
            print("Invalid TELEGRAM_THREAD_ID")

    try:
        r = requests.post(url, json=payload, timeout=10)
        print("Telegram:", r.status_code)
    except Exception as e:
        print("Telegram error:", repr(e))


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

    try:
        for entry in data.get("entry", []):
            for m in entry.get("messaging", []):
                msg = m.get("message", {}) or {}
                text = msg.get("text")
                if not text:
                    continue

                sender_id = (m.get("sender", {}) or {}).get("id", "unknown")
                category = classify(text)
                username = get_username_from_graph(sender_id)

                out = build_message(category, username, sender_id, text)
                send_to_telegram(out)

    except Exception as e:
        print("Parse error:", repr(e))

    return "OK", 200


@app.get("/")
def health():
    return "OK", 200
