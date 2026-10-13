from dataclasses import dataclass, field
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
    name: str = ""
    dates: list = field(default_factory=list)  # aligned with closes
    opens: list = field(default_factory=list)
    highs: list = field(default_factory=list)
    lows: list = field(default_factory=list)
    volumes: list = field(default_factory=list)  # None where Yahoo has no volume

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
    tz = timezone(timedelta(seconds=meta.get("gmtoffset", 7 * 3600)))
    day = lambda ts: datetime.fromtimestamp(ts, tz).date()
    q = ((r.get("indicators") or {}).get("quote") or [{}])[0]
    stamps = r.get("timestamp") or []
    col = lambda k: (q.get(k) or [None] * len(stamps))[: len(stamps)]
    # mỗi dòng: [timestamp, open, high, low, close, volume]
    rows = [list(x) for x in zip(stamps, col("open"), col("high"), col("low"), col("close"), col("volume"))]

    # Yahoo đôi khi để trống nến phiên trước, khi đó nến liền trước là của phiên cũ hơn.
    # Giá tham chiếu đúng = giá - thay đổi trong ngày (meta), dùng nó để lấp nến trống.
    ref = None
    change, mtime = meta.get("fulldayChange"), meta.get("regularMarketTime")
    if rows and rows[-1][4] is not None and change is not None and mtime and day(mtime) == day(rows[-1][0]):
        ref = rows[-1][4] - change
        if len(rows) >= 2 and rows[-2][4] is None:
            rows[-2][1:5] = [ref] * 4

    bars = [b for b in rows if b[4] is not None]
    if len(bars) < 2:
        raise QuoteError(f"{symbol}: không đủ dữ liệu giá")
    pick = lambda i: [b[i] if b[i] is not None else b[4] for b in bars]
    return Quote(
        symbol=symbol,
        exchange=_exchange(meta.get("fullExchangeName") or meta.get("exchangeName")),
        price=bars[-1][4],
        prev_close=ref or bars[-2][4],
        closes=[b[4] for b in bars],
        trading_date=day(bars[-1][0]),
        name=meta.get("longName") or meta.get("shortName") or "",
        dates=[day(b[0]) for b in bars],
        opens=pick(1),
        highs=pick(2),
        lows=pick(3),
        volumes=[b[5] for b in bars],
    )


def fetch_quote(symbol: str, timeout: int = 15, period: str = "3mo") -> Quote:
    try:
        resp = requests.get(
            URL.format(symbol=symbol),
            params={"range": period, "interval": "1d"},
            headers=HEADERS,
            timeout=timeout,
        )
        resp.raise_for_status()
        return parse(symbol, resp.json())
    except requests.RequestException as e:
        raise QuoteError(f"{symbol}: lỗi gọi Yahoo ({e})") from e
    except ValueError as e:
        raise QuoteError(f"{symbol}: phản hồi không hợp lệ") from e
