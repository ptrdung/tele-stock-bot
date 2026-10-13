import requests

API = "https://api.telegram.org/bot{token}/{method}"


def _call(token: str, method: str, timeout: int = 15, **kw) -> dict:
    data = requests.post(API.format(token=token, method=method), timeout=timeout, **kw).json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram {method}: {data.get('description')}")
    return data.get("result")


def send_message(token: str, chat_id: str, text: str):
    _call(token, "sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})


def send_photo(token: str, chat_id: str, png: bytes, caption: str = ""):
    """Gửi ảnh, chú thích (HTML, tối đa 1024 ký tự) nằm phía trên ảnh."""
    _call(token, "sendPhoto", timeout=30,
          data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML", "show_caption_above_media": "true"},
          files={"photo": ("chart.png", png, "image/png")})


def get_updates(token: str, offset: int = 0, timeout: int = 50) -> list:
    """Long-polling: chờ tối đa `timeout` giây đến khi có tin nhắn mới."""
    return _call(token, "getUpdates", timeout=timeout + 10,
                 json={"offset": offset, "timeout": timeout, "allowed_updates": ["message"]})
