from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import requests

URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}


class QuoteError(Exception):
    pass


@dataclass
class Quote:
    symbol: str  # e.g. VNM.VN
    exchange: str  # HOSE / HNX / UPCOM
    price: float
    prev_close: float
    closes: list  # daily closes, oldest first, last one is `price`
    trading_date: date  # date of the latest bar

    @property
    def ticker(self) -> str:
        return self.symbol.split(".")[0]

    @property
    def change_pct(self) -> float:
        return (self.price / self.prev_close - 1) * 100


def normalize(symbol: str) -> str:
    s = symbol.strip().upper()
    return s if "." in s else s + ".VN"


def _exchange(name: str) -> str:
    n = (name or "").upper()
    if "HNX" in n or "HANOI" in n:
        return "HNX"
    if "UPCOM" in n:
        return "UPCOM"
    return "HOSE"


def parse(symbol: str, payload: dict) -> Quote:
    result = (payload.get("chart") or {}).get("result")
    if not result:
        raise QuoteError(f"{symbol}: không có dữ liệu")
    r = result[0]
    meta = r.get("meta", {})
    stamps = r.get("timestamp") or []
    raw = ((r.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
    bars = [(t, c) for t, c in zip(stamps, raw) if c is not None]
    if len(bars) < 2:
        raise QuoteError(f"{symbol}: không đủ dữ liệu giá")
    tz = timezone(timedelta(seconds=meta.get("gmtoffset", 7 * 3600)))
    return Quote(
        symbol=symbol,
        exchange=_exchange(meta.get("fullExchangeName") or meta.get("exchangeName")),
        price=bars[-1][1],
        prev_close=bars[-2][1],
        closes=[c for _, c in bars],
        trading_date=datetime.fromtimestamp(bars[-1][0], tz).date(),
    )


def fetch_quote(symbol: str, timeout: int = 15) -> Quote:
    try:
        resp = requests.get(
            URL.format(symbol=symbol),
            params={"range": "3mo", "interval": "1d"},
            headers=HEADERS,
            timeout=timeout,
        )
        resp.raise_for_status()
        return parse(symbol, resp.json())
    except requests.RequestException as e:
        raise QuoteError(f"{symbol}: lỗi gọi Yahoo ({e})") from e
    except ValueError as e:
        raise QuoteError(f"{symbol}: phản hồi không hợp lệ") from e
