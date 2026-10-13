import argparse
import logging
import os
import sys
import threading
import time
from datetime import datetime, timedelta, timezone

from . import bot, chart, lookup, summary
from .config import load, load_dotenv
from .telegram import send_message
from .yahoo import QuoteError, fetch_quote, normalize

log = logging.getLogger("stockbot")
ICT = timezone(timedelta(hours=7))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Tổng kết cuối phiên cổ phiếu VN gửi Telegram")
    ap.add_argument("--force", action="store_true", help="gửi dù hôm nay không phải ngày giao dịch")
    ap.add_argument("--daemon", action="store_true",
                    help="chạy liên tục: nhận lệnh tra cứu và tự gửi tổng kết theo SEND_TIMES (mặc định 15:15, 15:30 giờ VN) T2–T6")
    ap.add_argument("--lookup", metavar="MÃ", help="gửi thông tin + biểu đồ của một mã (kèm --dry-run: in ra và lưu <MÃ>.png)")
    ap.add_argument("--dry-run", action="store_true", help="in ra màn hình, không gửi Telegram")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv()

    if args.daemon:
        return daemon()
    if args.lookup:
        return lookup_once(args.lookup, args.dry_run)

    cfg = load() if not args.dry_run else _dry_cfg()
    quotes, errors = [], []
    for s in cfg.symbols:
        try:
            quotes.append(fetch_quote(normalize(s)))
        except QuoteError as e:
            log.warning("%s", e)
            errors.append(s)
    if not quotes:
        log.error("không lấy được mã nào")
        return 1

    today = datetime.now(ICT).date()
    if max(q.trading_date for q in quotes) != today and not args.force:
        log.info("Hôm nay (%s) không có phiên giao dịch, bỏ qua", today)
        return 0

    text = summary.build(quotes, errors, cfg)
    if args.dry_run:
        print(text)
        return 0
    for chat in cfg.chat_ids:
        send_message(cfg.token, chat, text)
    log.info("Đã gửi tổng kết tới %d chat", len(cfg.chat_ids))
    return 0


def send_times() -> list:
    """Giờ gửi trong ngày (giờ VN), lấy từ SEND_TIMES="15:15,15:30"."""
    raw = os.environ.get("SEND_TIMES", "15:15,15:30")
    return sorted(tuple(int(x) for x in t.split(":")) for t in raw.replace(",", " ").split())


def next_run(now: datetime, times=((15, 15), (15, 30))) -> datetime:
    """Lần gửi kế tiếp: mốc giờ VN gần nhất sau `now`, chỉ T2–T6."""
    day = now.replace(second=0, microsecond=0)
    while True:
        if day.weekday() < 5:
            for h, m in times:
                t = day.replace(hour=h, minute=m)
                if t > now:
                    return t
        day += timedelta(days=1)


def lookup_once(symbol: str, dry_run: bool) -> int:
    cfg = _dry_cfg() if dry_run else load()
    if not dry_run:
        for chat in cfg.chat_ids:
            bot.send_lookup(cfg, chat, symbol)
        log.info("Đã gửi tra cứu %s tới %d chat", symbol.upper(), len(cfg.chat_ids))
        return 0
    try:
        q = fetch_quote(normalize(symbol), period="1y")
    except QuoteError as e:
        log.error("%s", e)
        return 1
    print(lookup.build(q, cfg))
    path = f"{q.ticker}.png"
    with open(path, "wb") as f:
        f.write(chart.render(q))
    log.info("Đã lưu biểu đồ: %s", path)
    return 0


def daemon() -> int:
    cfg = load()  # báo lỗi cấu hình ngay khi khởi động
    threading.Thread(target=_schedule, name="schedule", daemon=True).start()
    bot.poll(cfg)


def _schedule():
    """Gửi tổng kết theo SEND_TIMES, chạy ở luồng riêng."""
    while True:
        target = next_run(datetime.now(ICT), send_times())
        log.info("Lần gửi kế tiếp: %s", target)
        while (left := (target - datetime.now(ICT)).total_seconds()) > 0:
            time.sleep(min(left, 300))
        try:
            main([])
        except Exception:
            log.exception("gửi tổng kết lỗi")
        time.sleep(60)  # tránh chạy lặp trong cùng phút


def _dry_cfg():
    from .config import Config, read_watchlist
    wl = os.environ.get("WATCHLIST") or open(os.environ.get("WATCHLIST_FILE", "watchlist.txt")).read()
    return Config(token="", symbols=read_watchlist(wl))


if __name__ == "__main__":
    sys.exit(main())
