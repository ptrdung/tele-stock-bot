"""Biểu đồ giá dạng PNG.

matplotlib chỉ được import ở lần vẽ đầu tiên, nên bot không tốn thêm RAM khi chưa ai tra cứu.
Dùng `Figure` trực tiếp (không qua pyplot) để hình vẽ không bị giữ lại trong bộ nhớ toàn cục.
"""
import ctypes
import io

from .indicators import sma
from .yahoo import Quote

UP, DOWN = "#16a34a", "#dc2626"
_libc = None


def _release_memory():
    """Trả phần RAM đã giải phóng về cho hệ điều hành (chỉ có trên glibc)."""
    global _libc
    try:
        _libc = _libc or ctypes.CDLL("libc.so.6")
        _libc.malloc_trim(0)
    except (OSError, AttributeError):
        pass


def render(q: Quote, sessions: int = 63) -> bytes:
    """Biểu đồ ~3 tháng: giá đóng cửa, MA20, MA50 và khối lượng."""
    from matplotlib.figure import Figure
    from matplotlib.ticker import FuncFormatter

    n = min(sessions, len(q.closes))
    closes, dates = q.closes[-n:], q.dates[-n:]
    vols = [v or 0 for v in q.volumes[-n:]] if q.volumes else [0] * n
    ma20, ma50 = sma(q.closes, 20)[-n:], sma(q.closes, 50)[-n:]
    x = range(n)

    fig = Figure(figsize=(8, 4.8), dpi=100)
    ax, axv = fig.subplots(2, 1, sharex=True, gridspec_kw={"height_ratios": [3, 1], "hspace": 0.05})

    ax.plot(x, closes, color="#2563eb", lw=1.8, label="Giá")
    ax.fill_between(x, closes, min(closes), color="#2563eb", alpha=0.08)
    ax.plot(x, ma20, color="#f59e0b", lw=1.1, label="MA20")
    ax.plot(x, ma50, color="#8b5cf6", lw=1.1, label="MA50")
    ax.axhline(q.price, color="#6b7280", lw=0.8, ls=":")
    ax.annotate(f"{q.price:,.0f}", (n - 1, q.price), xytext=(4, 0), textcoords="offset points",
                va="center", fontsize=9, color=UP if q.change_pct >= 0 else DOWN, weight="bold")
    ax.set_title(f"{q.ticker} · {n} phiên gần nhất", loc="left", fontsize=11, weight="bold")
    ax.legend(loc="upper left", fontsize=8, frameon=False, ncol=3)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))

    colors = [UP if i == 0 or closes[i] >= closes[i - 1] else DOWN for i in range(n)]
    axv.bar(x, vols, color=colors, width=0.8)
    axv.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v / 1e6:.0f}tr" if v else ""))
    axv.set_ylabel("KL", fontsize=8)

    step = max(1, n // 6)
    axv.set_xticks(list(range(0, n, step)))
    axv.set_xticklabels([f"{d:%d/%m}" for d in dates[::step]], fontsize=8)
    for a in (ax, axv):
        a.grid(alpha=0.25)
        a.tick_params(labelsize=8)
        a.spines[["top", "right"]].set_visible(False)
        a.set_xlim(-1, n + 3)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    del fig, ax, axv
    _release_memory()
    return buf.getvalue()
