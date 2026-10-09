def rsi(closes: list, period: int = 14):
    """Wilder's RSI of the last close. None if there is not enough data."""
    if len(closes) < period + 1:
        return None
    deltas = [b - a for a, b in zip(closes, closes[1:])]
    gains = [max(d, 0) for d in deltas]
    losses = [max(-d, 0) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for g, l in zip(gains[period:], losses[period:]):
        avg_gain = (avg_gain * (period - 1) + g) / period
        avg_loss = (avg_loss * (period - 1) + l) / period
    if avg_loss == 0:
        return 100.0
    return 100 - 100 / (1 + avg_gain / avg_loss)
