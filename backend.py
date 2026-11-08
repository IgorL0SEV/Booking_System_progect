"""Бизнес-логика мини-системы бронирования.

Слой между CLI (app.py) и драйвером базы (postgres_driver.py):
полный CRUD для пользователей, столов и бронирований и проверка
пересекающихся бронирований по одному столу.
"""

from __future__ import annotations

from datetime import datetime

import psycopg2

from models.booking import Booking
from models.table import Table
from models.user import User
from postgres_driver import PostgresDriver


class BookingError(Exception):
    """Нарушение бизнес-правила (неверные данные, объект не найден)."""


class BookingConflict(BookingError):
    """Стол уже занят в запрошенный интервал."""


class BookingBackend:
    """Операции над пользователями, столами и бронированиями."""

    SELECT_BOOKINGS = """
        SELECT b.id, b.user_id, b.table_id, b.start_time, b.end_time,
               u.name, t.number, b.created_at
        FROM bookings b
        JOIN users u ON u.id = b.user_id
        JOIN tables t ON t.id = b.table_id
    """

    def __init__(self, driver: PostgresDriver) -> None:
        self.driver = driver

    @classmethod
    def from_env(cls) -> "BookingBackend":
        return cls(PostgresDriver.from_env())

    def __enter__(self) -> "BookingBackend":
        self.driver.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.driver.close()

    def init_schema(self) -> None:
        """Создаёт таблицы users, tables, bookings, если их ещё нет."""
        self.driver.create_tables()

    # --- пользователи -----------------------------------------------

    def create_user(self, name: str, phone: str) -> User:
        name, phone = name.strip(), phone.strip()
        if not name or not phone:
            raise BookingError("Имя и телефон обязательны.")
        try:
            user_id = self.driver.insert_returning_id(
                "INSERT INTO users (name, phone) VALUES (%s, %s) RETURNING id;",
                (name, phone),
            )
        except psycopg2.errors.UniqueViolation as exc:
            raise BookingError(f"Пользователь с телефоном {phone} уже есть.") from exc
        user = self.get_user(user_id)
        assert user is not None
        return user

    def get_user(self, user_id: int) -> User | None:
        row = self.driver.fetch_one(
            "SELECT id, name, phone, created_at FROM users WHERE id = %s;",
            (user_id,),
        )
        return User.from_row(row) if row else None

    def get_all_users(self) -> list[User]:
        rows = self.driver.fetch_all(
            "SELECT id, name, phone, created_at FROM users ORDER BY id;"
        )
        return [User.from_row(row) for row in rows]

    def update_user(
        self, user_id: int, name: str | None = None, phone: str | None = None
    ) -> User:
        fields: list[str] = []
        values: list[object] = []
        if name is not None:
            fields.append("name = %s")
            values.append(name.strip())
        if phone is not None:
            fields.append("phone = %s")
            values.append(phone.strip())
        if not fields:
            raise BookingError("Нечего обновлять: укажите имя или телефон.")
        values.append(user_id)
        try:
            affected = self.driver.execute(
                f"UPDATE users SET {', '.join(fields)} WHERE id = %s;", values
            )
        except psycopg2.errors.UniqueViolation as exc:
            raise BookingError("Такой телефон уже занят другим пользователем.") from exc
        if not affected:
            raise BookingError(f"Пользователь #{user_id} не найден.")
        user = self.get_user(user_id)
        assert user is not None
        return user

    def delete_user(self, user_id: int) -> bool:
        return self.driver.execute("DELETE FROM users WHERE id = %s;", (user_id,)) > 0

    # --- столы -------------------------------------------------------

    def create_table(self, number: int, seats: int, location: str | None = None) -> Table:
        if number <= 0:
            raise BookingError("Номер стола должен быть положительным.")
        if seats < 1:
            raise BookingError("Количество мест должно быть не меньше 1.")
        try:
            table_id = self.driver.insert_returning_id(
                "INSERT INTO tables (number, seats, location) "
                "VALUES (%s, %s, %s) RETURNING id;",
                (number, seats, location or None),
            )
        except psycopg2.errors.UniqueViolation as exc:
            raise BookingError(f"Стол №{number} уже существует.") from exc
        table = self.get_table(table_id)
        assert table is not None
        return table

    def get_table(self, table_id: int) -> Table | None:
        row = self.driver.fetch_one(
            "SELECT id, number, seats, location FROM tables WHERE id = %s;",
            (table_id,),
        )
        return Table.from_row(row) if row else None

    def get_all_tables(self) -> list[Table]:
        rows = self.driver.fetch_all(
            "SELECT id, number, seats, location FROM tables ORDER BY number;"
        )
        return [Table.from_row(row) for row in rows]

    def update_table(
        self,
        table_id: int,
        number: int | None = None,
        seats: int | None = None,
        location: str | None = None,
    ) -> Table:
        fields: list[str] = []
        values: list[object] = []
        if number is not None:
            fields.append("number = %s")
            values.append(number)
        if seats is not None:
            fields.append("seats = %s")
            values.append(seats)
        if location is not None:
            fields.append("location = %s")
            values.append(location)
        if not fields:
            raise BookingError("Нечего обновлять: укажите номер, места или зал.")
        values.append(table_id)
        try:
            affected = self.driver.execute(
                f"UPDATE tables SET {', '.join(fields)} WHERE id = %s;", values
            )
        except psycopg2.errors.UniqueViolation as exc:
            raise BookingError("Стол с таким номером уже существует.") from exc
        if not affected:
            raise BookingError(f"Стол #{table_id} не найден.")
        table = self.get_table(table_id)
        assert table is not None
        return table

    def delete_table(self, table_id: int) -> bool:
        return self.driver.execute("DELETE FROM tables WHERE id = %s;", (table_id,)) > 0

    # --- бронирования ------------------------------------------------

    def check_table_availability(
        self,
        table_id: int,
        start_time: datetime,
        end_time: datetime,
        ignore_booking_id: int | None = None,
    ) -> bool:
        """Свободен ли стол в интервале [start_time, end_time).

        Пересечением считается любая бронь, у которой начало раньше нового
        окончания и окончание позже нового начала. Соседние интервалы
        (конец предыдущей = начало новой) не пересекаются.
        """
        if end_time <= start_time:
            raise BookingError("Время окончания должно быть позже начала.")
        ignore = ignore_booking_id if ignore_booking_id is not None else -1
        row = self.driver.fetch_one(
            """
            SELECT COUNT(*)
            FROM bookings
            WHERE table_id = %s
              AND id <> %s
              AND start_time < %s
              AND end_time > %s;
            """,
            (table_id, ignore, end_time, start_time),
        )
        return bool(row) and row[0] == 0

    def create_booking(
        self,
        user_id: int,
        table_id: int,
        start_time: datetime,
        end_time: datetime,
    ) -> Booking:
        if self.get_user(user_id) is None:
            raise BookingError(f"Пользователь #{user_id} не найден.")
        if self.get_table(table_id) is None:
            raise BookingError(f"Стол #{table_id} не найден.")
        if not self.check_table_availability(table_id, start_time, end_time):
            raise BookingConflict(
                f"Стол #{table_id} занят в интервале "
                f"{start_time:%d.%m.%Y %H:%M}–{end_time:%H:%M}."
            )
        booking_id = self.driver.insert_returning_id(
            "INSERT INTO bookings (user_id, table_id, start_time, end_time) "
            "VALUES (%s, %s, %s, %s) RETURNING id;",
            (user_id, table_id, start_time, end_time),
        )
        booking = self.get_booking(booking_id)
        assert booking is not None
        return booking

    def get_booking(self, booking_id: int) -> Booking | None:
        row = self.driver.fetch_one(
            self.SELECT_BOOKINGS + " WHERE b.id = %s;", (booking_id,)
        )
        return Booking.from_row(row) if row else None

    def get_all_bookings(self) -> list[Booking]:
        rows = self.driver.fetch_all(
            self.SELECT_BOOKINGS + " ORDER BY b.start_time, b.id;"
        )
        return [Booking.from_row(row) for row in rows]

    def update_booking(
        self,
        booking_id: int,
        user_id: int | None = None,
        table_id: int | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> Booking:
        current = self.get_booking(booking_id)
        if current is None:
            raise BookingError(f"Бронирование #{booking_id} не найдено.")
        new_user = user_id if user_id is not None else current.user_id
        new_table = table_id if table_id is not None else current.table_id
        new_start = start_time if start_time is not None else current.start_time
        new_end = end_time if end_time is not None else current.end_time
        if self.get_user(new_user) is None:
            raise BookingError(f"Пользователь #{new_user} не найден.")
        if self.get_table(new_table) is None:
            raise BookingError(f"Стол #{new_table} не найден.")
        if not self.check_table_availability(
            new_table, new_start, new_end, ignore_booking_id=booking_id
        ):
            raise BookingConflict(
                f"Стол #{new_table} занят в интервале "
                f"{new_start:%d.%m.%Y %H:%M}–{new_end:%H:%M}."
            )
        self.driver.execute(
            "UPDATE bookings SET user_id = %s, table_id = %s, "
            "start_time = %s, end_time = %s WHERE id = %s;",
            (new_user, new_table, new_start, new_end, booking_id),
        )
        updated = self.get_booking(booking_id)
        assert updated is not None
        return updated

    def delete_booking(self, booking_id: int) -> bool:
        return (
            self.driver.execute("DELETE FROM bookings WHERE id = %s;", (booking_id,))
            > 0
        )
