import math
from dataclasses import dataclass

from .indicators import rsi
from .yahoo import Quote

# Biên độ dao động theo sàn
LIMITS = {"HOSE": 0.07, "HNX": 0.10, "UPCOM": 0.15}


@dataclass(frozen=True)
class Alert:
    kind: str  # rsi | floor | drop
    text: str


def _tick(exchange: str, price: float) -> int:
    if exchange != "HOSE":
        return 100
    if price < 10_000:
        return 10
    if price < 50_000:
        return 50
    return 100


def floor_price(exchange: str, ref: float) -> float:
    """Giá sàn = giá tham chiếu - biên độ, làm tròn lên theo bước giá."""
    raw = ref * (1 - LIMITS[exchange])
    tick = _tick(exchange, raw)
    return math.ceil(round(raw / tick, 6)) * tick


def evaluate(q: Quote, rsi_period=14, rsi_threshold=30.0, drop_threshold=6.0) -> list:
    alerts = []
    pct = q.change_pct

    r = rsi(q.closes, rsi_period)
    if r is not None and r < rsi_threshold:
        alerts.append(Alert("rsi", f"📉 RSI({rsi_period}) = {r:.1f} < {rsi_threshold:g} (vùng quá bán)"))

    floor = floor_price(q.exchange, q.prev_close)
    if q.price <= floor:
        alerts.append(Alert("floor", f"🧊 Giá {q.price:,.0f} chạm/thủng giá sàn {floor:,.0f} ({q.exchange})"))

    if pct <= -drop_threshold:
        alerts.append(Alert("drop", f"🔻 Giảm {abs(pct):.2f}% so với tham chiếu {q.prev_close:,.0f}"))

    return alerts
