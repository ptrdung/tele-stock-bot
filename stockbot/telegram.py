import requests


def send_message(token: str, chat_id: str, text: str):
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        timeout=15,
    )
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram sendMessage: {data.get('description')}")
