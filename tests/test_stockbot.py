import importlib.util
import unittest
from datetime import date, datetime, timezone

from stockbot import alerts, lookup, summary
from stockbot.config import Config, read_watchlist
from stockbot.indicators import rsi
from stockbot.yahoo import Quote, normalize


def quote(price, prev, exchange="HOSE", closes=None, ticker="AAA"):
    return Quote(f"{ticker}.VN", exchange, price, prev, closes or [prev, price], date(2026, 10, 9))


class Tests(unittest.TestCase):
    def test_rsi_monotonic(self):
        self.assertEqual(rsi(list(range(1, 30))), 100.0)
        self.assertLess(rsi(list(range(30, 1, -1))), 1)
        self.assertIsNone(rsi([1, 2, 3]))

    def test_floor_price(self):
        self.assertEqual(alerts.floor_price("HOSE", 100_000), 93_000)
        self.assertEqual(alerts.floor_price("HOSE", 20_000), 18_600)
        self.assertEqual(alerts.floor_price("HNX", 20_000), 18_000)
        self.assertEqual(alerts.floor_price("UPCOM", 10_000), 8_500)

    def test_alert_kinds(self):
        kinds = lambda q: [a.kind for a in alerts.evaluate(q)]
        self.assertEqual(kinds(quote(99_000, 100_000)), [])
        self.assertEqual(kinds(quote(93_000, 100_000)), ["floor", "drop"])
        self.assertEqual(kinds(quote(94_000, 100_000)), ["drop"])
        self.assertEqual(kinds(quote(94_100, 100_000)), [])  # -5.9%
        falling = [100 - i for i in range(20)]
        self.assertEqual(kinds(quote(81, 82, closes=falling)), ["rsi"])

    def test_normalize(self):
        self.assertEqual(normalize(" vnm "), "VNM.VN")
        self.assertEqual(normalize("VNM.VN"), "VNM.VN")

    def test_watchlist(self):
        self.assertEqual(read_watchlist("# c\nvnm, hpg\nVNM fpt # x"), ["VNM", "HPG", "FPT"])

    def test_next_run(self):
        from datetime import datetime
        from stockbot.__main__ import ICT, next_run
        at = lambda d, h, m: datetime(2026, 10, d, h, m, tzinfo=ICT)
        self.assertEqual(next_run(at(9, 10, 0)), at(9, 15, 15))    # Fri sáng
        self.assertEqual(next_run(at(9, 15, 15)), at(9, 15, 30))   # Fri 15:15 -> 15:30
        self.assertEqual(next_run(at(9, 15, 30)), at(12, 15, 15))  # Fri 15:30 -> Mon
        self.assertEqual(next_run(at(10, 9, 0)), at(12, 15, 15))   # Sat -> Mon
        self.assertEqual(next_run(at(9, 16, 0), [(15, 15)]), at(12, 15, 15))

    def test_send_times(self):
        from unittest import mock
        from stockbot.__main__ import send_times
        with mock.patch.dict("os.environ", {"SEND_TIMES": "15:30, 9:05"}):
            self.assertEqual(send_times(), [(9, 5), (15, 30)])

    def test_summary(self):
        cfg = Config(token="x")
        text = summary.build([quote(90_000, 100_000, ticker="BAD"), quote(100_500, 100_000, ticker="OK")], ["ZZZ"], cfg)
        self.assertIn("09/10/2026", text)
        self.assertIn("Cần chú ý", text)
        self.assertIn("BAD", text.split("<pre>")[0])
        self.assertNotIn("OK", text.split("<pre>")[0])
        self.assertIn("Không lấy được: ZZZ", text)
        calm = summary.build([quote(100_500, 100_000)], [], cfg)
        self.assertIn("Không có mã nào", calm)

    def test_summary_escapes_html(self):
        from unittest import mock
        with mock.patch.object(alerts, "evaluate", return_value=[alerts.Alert("rsi", "RSI = 19.4 < 30")]):
            text = summary.build([quote(100_000, 100_000)], [], Config(token="x"))
        self.assertIn("RSI = 19.4 &lt; 30", text)
        self.assertNotIn("< 30", text)



def history(n=260, start=50_000.0, step=100.0):
    """Quote giả với n phiên tăng đều, đủ trường cho tra cứu và biểu đồ."""
    from datetime import timedelta
    d0 = date(2025, 10, 13)
    days = [d0 + timedelta(days=i * 7 // 5) for i in range(n)]
    closes = [start + i * step for i in range(n)]
    return Quote("AAA.VN", "HOSE", closes[-1], closes[-2], closes, days[-1], name="A & B Corp", dates=days,
                 opens=closes, highs=[c + 50 for c in closes], lows=[c - 50 for c in closes],
                 volumes=[1_000_000] * (n - 1) + [2_000_000])


class LookupTests(unittest.TestCase):
    def test_ceiling_price(self):
        self.assertEqual(alerts.ceiling_price("HOSE", 57_100), 61_000)
        self.assertEqual(alerts.ceiling_price("HOSE", 20_000), 21_400)
        self.assertEqual(alerts.ceiling_price("HNX", 20_000), 22_000)

    def test_sma(self):
        from stockbot.indicators import sma
        self.assertEqual(sma([1, 2, 3, 4], 2), [None, 1.5, 2.5, 3.5])

    def test_parse_fills_missing_previous_bar(self):
        from stockbot.yahoo import parse
        t = lambda d: int(datetime(2026, 10, d, 2, tzinfo=timezone.utc).timestamp())
        payload = {"chart": {"result": [{
            "meta": {"gmtoffset": 25200, "fullExchangeName": "HOSE", "longName": "FPT Corporation",
                     "fulldayChange": -800.0, "regularMarketTime": t(13) + 3600},
            "timestamp": [t(9), t(12), t(13)],
            "indicators": {"quote": [{"open": [57_000, None, 57_100], "high": [58_000, None, 57_400],
                                      "low": [56_900, None, 56_100], "close": [57_900, None, 56_300],
                                      "volume": [10, None, 20]}]}}]}}
        q = parse("FPT.VN", payload)
        self.assertEqual(q.prev_close, 57_100)  # không phải 57_900 của phiên 09/10
        self.assertEqual(q.closes, [57_900, 57_100, 56_300])
        self.assertEqual(q.volumes, [10, None, 20])
        self.assertEqual(q.name, "FPT Corporation")

    def test_build(self):
        text = lookup.build(history(), Config(token="x"))
        self.assertIn("<b>AAA</b> — A &amp; B Corp (HOSE)", text)
        self.assertIn("KL 2.0tr  (×2.0 TB20)", text)
        self.assertIn("RSI(14) 100 — quá mua", text)
        self.assertIn("MA20", text)
        self.assertIn("▲", text)
        self.assertIn("YTD +", text)
        self.assertLess(len(text), 1024)  # giới hạn chú thích ảnh của Telegram

    @unittest.skipUnless(importlib.util.find_spec("matplotlib"), "cần matplotlib")
    def test_chart_png(self):
        from stockbot import chart
        self.assertEqual(chart.render(history())[:8], b"\x89PNG\r\n\x1a\n")

    def test_handle_routing(self):
        from unittest import mock
        from stockbot import bot
        cfg = Config(token="x", chat_ids=["1"])
        with mock.patch.object(bot, "send_lookup") as look, mock.patch.object(bot, "send_message") as msg:
            bot.handle(cfg, "1", "fpt")
            bot.handle(cfg, "1", "/s@my_bot VNM")
            bot.handle(cfg, "1", "chào cả nhà")  # tin thường: bỏ qua
            bot.handle(cfg, "1", "/start")
        self.assertEqual([c.args[2] for c in look.call_args_list], ["fpt", "VNM"])
        self.assertEqual(msg.call_count, 1)


if __name__ == "__main__":
    unittest.main()
