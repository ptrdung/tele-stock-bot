import requests


class Telegram:
    def __init__(self, token: str):
        self.base = f"https://api.telegram.org/bot{token}"

    def call(self, method: str, http_timeout: int = 15, **params):
        r = requests.post(f"{self.base}/{method}", json=params, timeout=http_timeout)
        data = r.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram {method}: {data.get('description')}")
        return data["result"]

    def updates(self, offset: int, poll: int = 30) -> list:
        return self.call("getUpdates", http_timeout=poll + 10, offset=offset, timeout=poll)

    def send(self, chat_id: int, text: str, keyboard=None):
        extra = {"reply_markup": {"inline_keyboard": keyboard}} if keyboard else {}
        return self.call("sendMessage", chat_id=chat_id, text=text, **extra)

    def edit_keyboard(self, chat_id: int, message_id: int, keyboard):
        return self.call("editMessageReplyMarkup", chat_id=chat_id, message_id=message_id,
                         reply_markup={"inline_keyboard": keyboard})

    def answer(self, callback_id: str, text: str = ""):
        return self.call("answerCallbackQuery", callback_query_id=callback_id, text=text)
