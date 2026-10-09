import unittest
from datetime import date

from stockbot import alerts
from stockbot.bot import Bot, market_open
from stockbot.config import Config
from stockbot.indicators import rsi
from stockbot.storage import Storage
from stockbot.yahoo import Quote, normalize


def quote(price, prev, exchange="HOSE", closes=None):
    return Quote("AAA.VN", exchange, price, prev, closes or [prev, price], date(2026, 10, 9))


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

    def test_market_open(self):
        from datetime import datetime
        from stockbot.bot import ICT
        self.assertTrue(market_open(datetime(2026, 10, 9, 10, 0, tzinfo=ICT)))   # Fri
        self.assertFalse(market_open(datetime(2026, 10, 10, 10, 0, tzinfo=ICT)))  # Sat
        self.assertFalse(market_open(datetime(2026, 10, 9, 16, 0, tzinfo=ICT)))

    def test_scan_dedupes(self):
        sent = []

        class TG:
            def send(self, chat_id, text, keyboard=None):
                sent.append((chat_id, text))

        store = Storage(":memory:")
        store.add(1, "AAA.VN")
        bot = Bot(Config(token="x"), TG(), store, fetch=lambda s: quote(90_000, 100_000))
        bot.scan()
        bot.scan()
        self.assertEqual(len(sent), 1)
        self.assertIn("sàn", sent[0][1])
        self.assertIn("Giảm", sent[0][1])


if __name__ == "__main__":
    unittest.main()
