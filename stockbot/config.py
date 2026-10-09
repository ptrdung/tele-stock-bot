import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    token: str
    db_path: str = "stockbot.db"
    check_interval: int = 600  # seconds between market scans
    rsi_period: int = 14
    rsi_threshold: float = 30.0
    drop_threshold: float = 6.0  # percent
    market_hours_only: bool = True


def load() -> Config:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit("Thiếu biến môi trường TELEGRAM_BOT_TOKEN (lấy từ @BotFather)")
    return Config(
        token=token,
        db_path=os.environ.get("DB_PATH", "stockbot.db"),
        check_interval=int(os.environ.get("CHECK_INTERVAL", "600")),
        rsi_period=int(os.environ.get("RSI_PERIOD", "14")),
        rsi_threshold=float(os.environ.get("RSI_THRESHOLD", "30")),
        drop_threshold=float(os.environ.get("DROP_THRESHOLD", "6")),
        market_hours_only=os.environ.get("MARKET_HOURS_ONLY", "1") != "0",
    )
