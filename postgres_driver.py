"""Драйвер PostgreSQL для мини-системы бронирования.

Отвечает за соединение, создание схемы и низкоуровневые запросы.
Бизнес-логика — в backend.py, модели данных — в models/.
"""

from __future__ import annotations

import os
from typing import Any, Sequence

import psycopg2
from dotenv import load_dotenv

CREATE_USERS_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id         SERIAL PRIMARY KEY,
    name       TEXT NOT NULL,
    phone      TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
"""

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS tables (
    id       SERIAL PRIMARY KEY,
    number   INT NOT NULL UNIQUE CHECK (number > 0),
    seats    INT NOT NULL CHECK (seats >= 1),
    location TEXT
);
"""

CREATE_BOOKINGS_SQL = """
CREATE TABLE IF NOT EXISTS bookings (
    id         SERIAL PRIMARY KEY,
    user_id    INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    table_id   INT NOT NULL REFERENCES tables(id) ON DELETE CASCADE,
    start_time TIMESTAMP NOT NULL,
    end_time   TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT booking_time_valid CHECK (end_time > start_time)
);
"""

CREATE_INDEXES_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_bookings_table_time "
    "ON bookings (table_id, start_time, end_time);",
    "CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings (user_id);",
)

ALLOWED_TABLES = {"users", "tables", "bookings"}


def readable_server_error(exc: UnicodeDecodeError) -> str:
    """Достаёт текст ошибки сервера, который psycopg2 не смог раскодировать.

    На Windows PostgreSQL часто ставится с `lc_messages = 'Russian_Russia.1251'`:
    сообщение приходит в cp1251, psycopg2 ждёт UTF-8 и падает с
    UnicodeDecodeError раньше, чем показывает причину. Исходные байты
    остаются в атрибуте `object` — декодируем их сами.
    """
    raw = bytes(exc.object or b"")
    for encoding in ("cp1251", "utf-8"):
        try:
            return raw.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace").strip()


class PostgresDriver:
    """Тонкая обёртка над psycopg2: соединение, DDL и базовые запросы."""

    def __init__(
        self,
        host: str,
        port: int,
        dbname: str,
        user: str,
        password: str,
    ) -> None:
        self._params = {
            "host": host,
            "port": port,
            "dbname": dbname,
            "user": user,
            "password": password,
        }
        self._conn: psycopg2.extensions.connection | None = None

    # --- подключение -------------------------------------------------

    @classmethod
    def from_env(cls) -> "PostgresDriver":
        """Собирает драйвер из переменных окружения (.env)."""
        load_dotenv()
        required = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")
        missing = [name for name in required if not os.getenv(name)]
        if missing:
            raise RuntimeError(
                "Не заданы переменные окружения: "
                + ", ".join(missing)
                + ". Скопируйте .env.example в .env и заполните значения."
            )
        return cls(
            host=os.environ["DB_HOST"],
            port=int(os.environ["DB_PORT"]),
            dbname=os.environ["DB_NAME"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
        )

    def connect(self) -> "PostgresDriver":
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(**self._params)
        return self

    def close(self) -> None:
        if self._conn is not None and not self._conn.closed:
            self._conn.close()

    def __enter__(self) -> "PostgresDriver":
        return self.connect()

    def __exit__(self, exc_type, exc, tb) -> None:
        # Соединение закрывается всегда — даже при исключении внутри блока.
        self.close()

    @property
    def dbname(self) -> str:
        return str(self._params["dbname"])

    def _connection(self) -> psycopg2.extensions.connection:
        if self._conn is None or self._conn.closed:
            raise RuntimeError("Соединение не открыто: вызовите connect()")
        return self._conn

    # --- DDL ---------------------------------------------------------

    def create_tables(self) -> None:
        """Создаёт таблицы users, tables, bookings и индексы, если их ещё нет."""
        conn = self._connection()
        with conn, conn.cursor() as cur:
            cur.execute(CREATE_USERS_SQL)
            cur.execute(CREATE_TABLES_SQL)
            cur.execute(CREATE_BOOKINGS_SQL)
            for statement in CREATE_INDEXES_SQL:
                cur.execute(statement)

    # --- запросы -----------------------------------------------------

    def fetch_all(
        self, sql: str, params: Sequence[Any] | None = None
    ) -> list[tuple]:
        with self._connection().cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def fetch_one(
        self, sql: str, params: Sequence[Any] | None = None
    ) -> tuple | None:
        with self._connection().cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> int:
        """Выполняет INSERT/UPDATE/DELETE, возвращает число затронутых строк."""
        conn = self._connection()
        with conn, conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount

    def insert_returning_id(
        self, sql: str, params: Sequence[Any] | None = None
    ) -> int:
        """Выполняет INSERT с RETURNING id и возвращает новый идентификатор."""
        conn = self._connection()
        with conn, conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()[0]

    def count_rows(self, table: str) -> int:
        """Считает строки в таблице. Имя таблицы — только из белого списка."""
        if table not in ALLOWED_TABLES:
            raise ValueError(f"Неизвестная таблица: {table}")
        row = self.fetch_one(f"SELECT COUNT(*) FROM {table};")  # noqa: S608
        return int(row[0]) if row else 0
