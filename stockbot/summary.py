from datetime import date
from html import escape

from . import alerts
from .indicators import rsi
from .yahoo import Quote

ICON = {"rsi": "RSI", "floor": "SÀN", "drop": "GIẢM"}


def build(quotes: list, errors: list, cfg) -> str:
    """Tin tổng hợp cuối phiên: mục cần chú ý + bảng toàn bộ mã."""
    day = max(q.trading_date for q in quotes)
    rows, flagged = [], []
    for q in sorted(quotes, key=lambda q: q.change_pct):
        found = alerts.evaluate(q, cfg.rsi_period, cfg.rsi_threshold, cfg.drop_threshold)
        r = rsi(q.closes, cfg.rsi_period)
        rows.append(f"{q.ticker:<5} {q.price:>8,.0f} {q.change_pct:>+7.2f}% {('%.0f' % r) if r is not None else '-':>4}"
                    + ("  ⚠️" if found else ""))
        if found:
            flagged.append((q, found))

    out = [f"📊 <b>Tổng kết phiên {day:%d/%m/%Y}</b>"]
    if flagged:
        out.append("\n⚠️ <b>Cần chú ý</b>")
        for q, found in flagged:
            out.append(f"<b>{q.ticker}</b> ({q.exchange}) {q.price:,.0f} ₫ ({q.change_pct:+.2f}%)")
            out += [f"  {escape(a.text)}" for a in found]
    else:
        out.append("\n✅ Không có mã nào chạm ngưỡng cảnh báo.")
    header = f"{'Mã':<5} {'Giá':>8} {'%CĐ':>8} {'RSI':>4}"
    out.append("\n<pre>" + escape("\n".join([header] + rows)) + "</pre>")
    if errors:
        out.append("Không lấy được: " + escape(", ".join(errors)))
    return "\n".join(out)
