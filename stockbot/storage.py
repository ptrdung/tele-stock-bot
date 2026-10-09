import sqlite3


class Storage:
    def __init__(self, path: str):
        self.db = sqlite3.connect(path)
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS watch (
                chat_id INTEGER NOT NULL, symbol TEXT NOT NULL,
                PRIMARY KEY (chat_id, symbol));
            CREATE TABLE IF NOT EXISTS sent (
                chat_id INTEGER NOT NULL, symbol TEXT NOT NULL,
                kind TEXT NOT NULL, day TEXT NOT NULL,
                PRIMARY KEY (chat_id, symbol, kind, day));
            """
        )

    def add(self, chat_id: int, symbol: str):
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO watch VALUES (?, ?)", (chat_id, symbol))

    def remove(self, chat_id: int, symbol: str):
        with self.db:
            self.db.execute("DELETE FROM watch WHERE chat_id=? AND symbol=?", (chat_id, symbol))

    def symbols(self, chat_id: int) -> list:
        rows = self.db.execute("SELECT symbol FROM watch WHERE chat_id=? ORDER BY symbol", (chat_id,))
        return [r[0] for r in rows]

    def watchers(self) -> dict:
        """symbol -> [chat_id, ...]"""
        out = {}
        for chat_id, symbol in self.db.execute("SELECT chat_id, symbol FROM watch"):
            out.setdefault(symbol, []).append(chat_id)
        return out

    def mark_sent(self, chat_id: int, symbol: str, kind: str, day: str) -> bool:
        """True nếu đây là lần đầu (chưa gửi cảnh báo này trong ngày giao dịch)."""
        with self.db:
            cur = self.db.execute("INSERT OR IGNORE INTO sent VALUES (?, ?, ?, ?)", (chat_id, symbol, kind, day))
        return cur.rowcount == 1
