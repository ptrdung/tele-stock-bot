import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone

from . import summary
from .config import load
from .telegram import send_message
from .yahoo import QuoteError, fetch_quote, normalize

log = logging.getLogger("stockbot")
ICT = timezone(timedelta(hours=7))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Tổng kết cuối phiên cổ phiếu VN gửi Telegram")
    ap.add_argument("--force", action="store_true", help="gửi dù hôm nay không phải ngày giao dịch")
    ap.add_argument("--dry-run", action="store_true", help="in ra màn hình, không gửi Telegram")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

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


def _dry_cfg():
    import os
    from .config import Config, read_watchlist
    wl = os.environ.get("WATCHLIST") or open(os.environ.get("WATCHLIST_FILE", "watchlist.txt")).read()
    return Config(token="", symbols=read_watchlist(wl))


if __name__ == "__main__":
    sys.exit(main())
