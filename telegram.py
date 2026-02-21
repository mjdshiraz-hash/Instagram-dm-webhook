import requests

BOT_TOKEN = "PUT_YOUR_TOKEN"
CHAT_ID = "PUT_CHAT_ID"

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": text
    })
