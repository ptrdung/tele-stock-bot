import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Config:
    token: str
    chat_ids: list = field(default_factory=list)
    symbols: list = field(default_factory=list)
    rsi_period: int = 14
    rsi_threshold: float = 30.0
    drop_threshold: float = 6.0  # percent


def read_watchlist(text: str) -> list:
    """Mã cách nhau bởi khoảng trắng/dấu phẩy/xuống dòng; '#' bắt đầu chú thích."""
    out = []
    for line in text.splitlines():
        for tok in line.split("#")[0].replace(",", " ").split():
            if tok.upper() not in out:
                out.append(tok.upper())
    return out


def load() -> Config:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chats = [c for c in os.environ.get("TELEGRAM_CHAT_ID", "").replace(",", " ").split() if c]
    if not token or not chats:
        raise SystemExit("Thiếu TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID")
    wl = os.environ.get("WATCHLIST") or Path(os.environ.get("WATCHLIST_FILE", "watchlist.txt")).read_text()
    symbols = read_watchlist(wl)
    if not symbols:
        raise SystemExit("Danh sách theo dõi trống (watchlist.txt)")
    return Config(
        token=token,
        chat_ids=chats,
        symbols=symbols,
        rsi_period=int(os.environ.get("RSI_PERIOD", "14")),
        rsi_threshold=float(os.environ.get("RSI_THRESHOLD", "30")),
        drop_threshold=float(os.environ.get("DROP_THRESHOLD", "6")),
    )
