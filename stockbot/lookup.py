from datetime import date, timedelta
from html import escape

from . import alerts
from .indicators import rsi, sma
from .yahoo import Quote


def _pct(now: float, base) -> str:
    return f"{(now / base - 1) * 100:+.1f}%" if base else "-"


def _close_on_or_before(q: Quote, day: date):
    """Giá đóng cửa của phiên cuối cùng không muộn hơn `day`."""
    found = None
    for d, c in zip(q.dates, q.closes):
        if d > day:
            break
        found = c
    return found


def _volume(v: float) -> str:
    return f"{v / 1e6:.1f}tr" if v >= 1e6 else f"{v / 1e3:.0f}k"


def _rsi_label(r: float, threshold: float) -> str:
    if r < threshold:
        return "quá bán ⚠️"
    if r > 70:
        return "quá mua"
    return "trung tính"


def build(q: Quote, cfg) -> str:
    """Tin tra cứu một mã (HTML, đủ ngắn để làm chú thích ảnh)."""
    last = q.dates[-1] if q.dates else q.trading_date
    name = f" — {escape(q.name)}" if q.name else ""
    out = [
        f"📈 <b>{q.ticker}</b>{name} ({q.exchange})",
        f"Giá <b>{q.price:,.0f}</b> ₫  ({q.change_pct:+.2f}%)  · phiên {last:%d/%m}",
        f"TC {q.prev_close:,.0f} | Trần {alerts.ceiling_price(q.exchange, q.prev_close):,.0f}"
        f" | Sàn {alerts.floor_price(q.exchange, q.prev_close):,.0f}",
    ]
    if q.opens:
        out.append(f"Mở {q.opens[-1]:,.0f} | Cao {q.highs[-1]:,.0f} | Thấp {q.lows[-1]:,.0f}")
    if q.volumes and q.volumes[-1] is not None:
        prev = [v for v in q.volumes[:-1] if v][-20:]
        ratio = f"  (×{q.volumes[-1] / (sum(prev) / len(prev)):.1f} TB20)" if prev else ""
        out.append(f"KL {_volume(q.volumes[-1])}{ratio}")

    out.append("")
    r = rsi(q.closes, cfg.rsi_period)
    if r is not None:
        out.append(f"RSI({cfg.rsi_period}) {r:.0f} — {_rsi_label(r, cfg.rsi_threshold)}")
    mas = []
    for n in (20, 50):
        m = sma(q.closes, n)[-1]
        if m is not None:
            mas.append(f"MA{n} {m:,.0f} {'▲' if q.price >= m else '▼'}")
    if mas:
        out.append(" | ".join(mas))
    perf = [
        f"1T {_pct(q.price, _close_on_or_before(q, last - timedelta(days=7)))}",
        f"1Th {_pct(q.price, _close_on_or_before(q, last - timedelta(days=30)))}",
        f"3Th {_pct(q.price, _close_on_or_before(q, last - timedelta(days=91)))}",
        f"YTD {_pct(q.price, _close_on_or_before(q, date(last.year - 1, 12, 31)))}",
    ]
    out.append(" | ".join(perf))
    if q.highs:
        hi, lo = max(q.highs), min(q.lows)
        out.append(f"52T: {lo:,.0f} – {hi:,.0f} (cách đỉnh {_pct(q.price, hi)})")

    for a in alerts.evaluate(q, cfg.rsi_period, cfg.rsi_threshold, cfg.drop_threshold):
        if a.kind != "rsi":  # RSI đã có ở dòng trên
            out.append(escape(a.text))
    return "\n".join(out)
