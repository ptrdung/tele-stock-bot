"""Nhận lệnh tra cứu mã cổ phiếu qua Telegram (long-polling)."""
import logging
import re
import time
from html import escape

from . import chart, lookup
from .telegram import get_updates, send_message, send_photo
from .yahoo import QuoteError, fetch_quote, normalize

log = logging.getLogger("stockbot")
TICKER = re.compile(r"^[A-Z0-9]{2,10}(\.[A-Z]+)?$")
HELP = ("Gõ mã cổ phiếu, ví dụ <code>FPT</code> hoặc <code>/s FPT</code>, "
        "để xem giá, chỉ báo và biểu đồ 3 tháng.")
MAX_AGE = 300  # bỏ qua tin nhắn cũ hơn 5 phút (ví dụ tồn lại khi bot khởi động lại)


def send_lookup(cfg, chat_id: str, symbol: str):
    try:
        q = fetch_quote(normalize(symbol), period="1y")
    except QuoteError as e:
        log.warning("%s", e)
        send_message(cfg.token, chat_id, f"Không lấy được dữ liệu mã <b>{escape(symbol.upper())}</b>. "
                                         "Yahoo Finance chủ yếu có mã sàn HOSE.")
        return
    caption = lookup.build(q, cfg)
    try:
        png = chart.render(q)
    except Exception:
        log.exception("vẽ biểu đồ %s lỗi", q.ticker)
        send_message(cfg.token, chat_id, caption)
        return
    send_photo(cfg.token, chat_id, png, caption)


def handle(cfg, chat_id: str, text: str):
    words = text.split()
    if not words:
        return
    cmd = words[0].split("@")[0].lower()  # "/s@ten_bot" trong nhóm
    if cmd in ("/start", "/help"):
        return send_message(cfg.token, chat_id, HELP)
    if cmd in ("/s", "/check"):
        words = words[1:]
    elif cmd.startswith("/"):
        return send_message(cfg.token, chat_id, HELP)
    if len(words) != 1 or not TICKER.match(words[0].upper()):
        if cmd in ("/s", "/check"):
            send_message(cfg.token, chat_id, HELP)
        return  # tin nhắn thường trong nhóm: bỏ qua
    send_lookup(cfg, chat_id, words[0])


def poll(cfg):
    """Chờ tin nhắn mới và trả lời; chỉ phục vụ các chat trong TELEGRAM_CHAT_ID."""
    allowed, offset = set(cfg.chat_ids), 0
    log.info("Bot sẵn sàng nhận lệnh")
    while True:
        try:
            updates = get_updates(cfg.token, offset)
        except Exception as e:
            log.warning("getUpdates lỗi: %s", e)
            time.sleep(5)
            continue
        for u in updates:
            offset = u["update_id"] + 1
            m = u.get("message") or {}
            chat_id, text = str((m.get("chat") or {}).get("id", "")), m.get("text") or ""
            if chat_id not in allowed or not text or time.time() - m.get("date", 0) > MAX_AGE:
                continue
            try:
                handle(cfg, chat_id, text)
            except Exception:
                log.exception("trả lời chat %s lỗi", chat_id)
