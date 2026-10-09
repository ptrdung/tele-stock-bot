import logging
import time
from datetime import datetime, timedelta, timezone

from . import alerts as alerts_mod
from .config import Config
from .storage import Storage
from .telegram import Telegram
from .yahoo import QuoteError, fetch_quote, normalize

log = logging.getLogger("stockbot")
ICT = timezone(timedelta(hours=7))

# Gợi ý sẵn để chọn nhanh (rổ VN30)
VN30 = ["ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG",
        "MBB", "MSN", "MWG", "PLX", "POW", "SAB", "SHB", "SSB", "SSI", "STB",
        "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE"]

HELP = (
    "Bot cảnh báo cổ phiếu Việt Nam (dữ liệu Yahoo Finance).\n\n"
    "/pick – chọn mã yêu thích từ danh sách VN30\n"
    "/add VNM HPG – thêm mã (cả mã ngoài VN30)\n"
    "/remove VNM – bỏ mã\n"
    "/list – xem danh sách đang theo dõi\n"
    "/check – kiểm tra ngay các mã của bạn\n\n"
    "Cảnh báo khi: RSI < 30 · giá chạm/thủng sàn · giảm từ 6% trở lên.\n"
    "Mỗi loại cảnh báo chỉ gửi 1 lần/mã/phiên."
)


def market_open(now=None) -> bool:
    now = now or datetime.now(ICT)
    return now.weekday() < 5 and (9, 0) <= (now.hour, now.minute) <= (15, 15)


def pick_keyboard(selected: set) -> list:
    rows, row = [], []
    for t in VN30:
        row.append({"text": ("✅ " if t in selected else "") + t, "callback_data": f"t:{t}"})
        if len(row) == 5:
            rows.append(row)
            row = []
    return rows + ([row] if row else [])


class Bot:
    def __init__(self, cfg: Config, tg: Telegram = None, store: Storage = None, fetch=fetch_quote):
        self.cfg = cfg
        self.tg = tg or Telegram(cfg.token)
        self.store = store or Storage(cfg.db_path)
        self.fetch = fetch

    # ---- commands -------------------------------------------------------
    def handle_message(self, chat_id: int, text: str):
        cmd, *args = text.strip().split()
        cmd = cmd.split("@")[0].lower()
        if cmd in ("/start", "/help"):
            self.tg.send(chat_id, HELP)
        elif cmd == "/pick":
            sel = {s.split(".")[0] for s in self.store.symbols(chat_id)}
            self.tg.send(chat_id, "Chạm để chọn/bỏ mã theo dõi:", pick_keyboard(sel))
        elif cmd == "/add":
            self.tg.send(chat_id, self._add(chat_id, args))
        elif cmd == "/remove":
            for a in args:
                self.store.remove(chat_id, normalize(a))
            self.tg.send(chat_id, self._list_text(chat_id))
        elif cmd == "/list":
            self.tg.send(chat_id, self._list_text(chat_id))
        elif cmd == "/check":
            self.tg.send(chat_id, self._status(chat_id))
        else:
            self.tg.send(chat_id, HELP)

    def handle_callback(self, cb: dict):
        data = cb.get("data", "")
        msg = cb["message"]
        chat_id = msg["chat"]["id"]
        if data.startswith("t:") and data[2:] in VN30:
            sym = normalize(data[2:])
            if sym in self.store.symbols(chat_id):
                self.store.remove(chat_id, sym)
            else:
                self.store.add(chat_id, sym)
            sel = {s.split(".")[0] for s in self.store.symbols(chat_id)}
            self.tg.edit_keyboard(chat_id, msg["message_id"], pick_keyboard(sel))
        self.tg.answer(cb["id"])

    def _add(self, chat_id: int, args: list) -> str:
        if not args:
            return "Dùng: /add VNM HPG"
        ok, bad = [], []
        for a in args:
            sym = normalize(a)
            try:
                self.fetch(sym)
            except QuoteError:
                bad.append(a.upper())
                continue
            self.store.add(chat_id, sym)
            ok.append(sym.split(".")[0])
        out = []
        if ok:
            out.append("Đã thêm: " + ", ".join(ok))
        if bad:
            out.append("Không tìm thấy trên Yahoo: " + ", ".join(bad))
        return "\n".join(out)

    def _list_text(self, chat_id: int) -> str:
        syms = [s.split(".")[0] for s in self.store.symbols(chat_id)]
        return "Đang theo dõi: " + ", ".join(syms) if syms else "Chưa theo dõi mã nào. Dùng /pick hoặc /add."

    def _status(self, chat_id: int) -> str:
        lines = []
        for sym in self.store.symbols(chat_id):
            try:
                q = self.fetch(sym)
            except QuoteError as e:
                lines.append(f"{sym}: lỗi ({e})")
                continue
            found = self.evaluate(q)
            flag = " ⚠️ " + ", ".join(a.kind for a in found) if found else ""
            lines.append(f"{q.ticker}: {q.price:,.0f} ({q.change_pct:+.2f}%){flag}")
        return "\n".join(lines) or self._list_text(chat_id)

    # ---- scanning -------------------------------------------------------
    def evaluate(self, q):
        c = self.cfg
        return alerts_mod.evaluate(q, c.rsi_period, c.rsi_threshold, c.drop_threshold)

    def scan(self):
        for sym, chats in self.store.watchers().items():
            try:
                q = self.fetch(sym)
            except QuoteError as e:
                log.warning("%s", e)
                continue
            found = self.evaluate(q)
            day = q.trading_date.isoformat()
            for chat_id in chats:
                fresh = [a for a in found if self.store.mark_sent(chat_id, sym, a.kind, day)]
                if fresh:
                    try:
                        self.tg.send(chat_id, alerts_mod.format_message(q, fresh))
                    except Exception:
                        log.exception("gửi tin thất bại chat=%s", chat_id)

    # ---- main loop ------------------------------------------------------
    def run(self):
        offset, next_scan = 0, 0.0
        log.info("Bot started")
        while True:
            if time.time() >= next_scan:
                next_scan = time.time() + self.cfg.check_interval
                if not self.cfg.market_hours_only or market_open():
                    try:
                        self.scan()
                    except Exception:
                        log.exception("scan lỗi")
            try:
                for u in self.tg.updates(offset, poll=30):
                    offset = u["update_id"] + 1
                    if "message" in u and u["message"].get("text"):
                        self.handle_message(u["message"]["chat"]["id"], u["message"]["text"])
                    elif "callback_query" in u:
                        self.handle_callback(u["callback_query"])
            except Exception:
                log.exception("lỗi khi xử lý update")
                time.sleep(5)
