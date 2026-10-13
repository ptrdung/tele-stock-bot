import unittest
from datetime import date

from stockbot import alerts, summary
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
        self.assertEqual(next_run(at(9, 15, 15)), at(12, 15, 15))  # Fri đúng giờ -> Mon
        self.assertEqual(next_run(at(10, 9, 0)), at(12, 15, 15))   # Sat -> Mon

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


if __name__ == "__main__":
    unittest.main()
