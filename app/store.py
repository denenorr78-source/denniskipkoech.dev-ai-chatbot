import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator


class Store:
    def __init__(self, database: str):
        self.database = database
        self.is_postgres = database.startswith(("postgres://", "postgresql://"))
        if "://" in database and not self.is_postgres:
            raise ValueError("DATABASE_URL must use PostgreSQL; SQLite accepts a filesystem path")
        if not self.is_postgres:
            Path(database).parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS conversations (
                platform TEXT NOT NULL,
                sender_id TEXT NOT NULL,
                state_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (platform, sender_id)
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS processed_events (
                platform TEXT NOT NULL,
                event_id TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (platform, event_id)
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS pending_events (
                platform TEXT NOT NULL,
                event_id TEXT NOT NULL,
                result_json TEXT NOT NULL,
                PRIMARY KEY (platform, event_id)
            )""")

    def _connect(self) -> Any:
        if self.is_postgres:
            import psycopg
            from psycopg.rows import dict_row

            return psycopg.connect(
                self.database,
                connect_timeout=10,
                row_factory=dict_row,
            )
        db = sqlite3.connect(self.database, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    @contextmanager
    def _connection(self) -> Generator[Any, None, None]:
        db = self._connect()
        try:
            with db:
                yield db
        finally:
            db.close()

    def _execute(self, db: Any, query: str, parameters: tuple[Any, ...] = ()) -> Any:
        if self.is_postgres:
            query = query.replace("?", "%s")
        return db.execute(query, parameters)

    def check(self) -> None:
        with self._connection() as db:
            self._execute(db, "SELECT 1")

    def load(self, platform: str, sender_id: str) -> dict[str, Any] | None:
        with self._connection() as db:
            row = self._execute(
                db,
                "SELECT state_json FROM conversations WHERE platform=? AND sender_id=?",
                (platform, sender_id),
            ).fetchone()
        return json.loads(row["state_json"]) if row else None

    def save(self, platform: str, sender_id: str, state: dict[str, Any]) -> None:
        with self._connection() as db:
            self._execute(
                db,
                """INSERT INTO conversations(platform, sender_id, state_json, updated_at)
                   VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(platform, sender_id) DO UPDATE SET
                     state_json=excluded.state_json, updated_at=CURRENT_TIMESTAMP""",
                (platform, sender_id, json.dumps(state, ensure_ascii=False)),
            )

    def is_processed(self, platform: str, event_id: str) -> bool:
        if not event_id:
            return False
        with self._connection() as db:
            row = self._execute(
                db,
                "SELECT 1 FROM processed_events WHERE platform=? AND event_id=?",
                (platform, event_id),
            ).fetchone()
        return row is not None

    def load_pending_event(self, platform: str, event_id: str) -> dict[str, Any] | None:
        if not event_id:
            return None
        with self._connection() as db:
            row = self._execute(
                db,
                "SELECT result_json FROM pending_events WHERE platform=? AND event_id=?",
                (platform, event_id),
            ).fetchone()
        return json.loads(row["result_json"]) if row else None

    def save_pending_event(
        self, platform: str, event_id: str, result: dict[str, Any]
    ) -> None:
        if not event_id:
            return
        with self._connection() as db:
            self._execute(
                db,
                """INSERT INTO pending_events(platform, event_id, result_json)
                   VALUES (?, ?, ?)
                   ON CONFLICT(platform, event_id) DO NOTHING""",
                (platform, event_id, json.dumps(result, ensure_ascii=False)),
            )

    def mark_processed(self, platform: str, event_id: str) -> None:
        if not event_id:
            return
        with self._connection() as db:
            if self.is_postgres:
                self._execute(
                    db,
                    """INSERT INTO processed_events(platform, event_id) VALUES (?, ?)
                       ON CONFLICT(platform, event_id) DO NOTHING""",
                    (platform, event_id),
                )
            else:
                self._execute(
                    db,
                    "INSERT OR IGNORE INTO processed_events(platform, event_id) VALUES (?, ?)",
                    (platform, event_id),
                )
            self._execute(
                db,
                "DELETE FROM pending_events WHERE platform=? AND event_id=?",
                (platform, event_id),
            )
