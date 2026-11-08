"""Наполняет базу демонстрационными данными (идемпотентно).

Создаёт ≥3 пользователей, ≥3 стола и ≥2 бронирования. Повторный запуск
ничего не дублирует: существующие записи переиспользуются.

    python seed_demo.py
"""

from __future__ import annotations

from datetime import datetime, timedelta

from backend import BookingBackend, BookingError

USERS = [
    ("Анна Смирнова", "+7 900 111-22-33"),
    ("Игорь Петров", "+7 900 222-33-44"),
    ("Мария Козлова", "+7 900 333-44-55"),
]

TABLES = [
    (1, 2, "у окна"),
    (2, 4, "в зале"),
    (3, 6, "терраса"),
]


def main() -> int:
    with BookingBackend.from_env() as backend:
        backend.init_schema()

        users = {user.phone: user for user in backend.get_all_users()}
        for name, phone in USERS:
            if phone not in users:
                users[phone] = backend.create_user(name, phone)
                print("  + пользователь", users[phone])

        tables = {table.number: table for table in backend.get_all_tables()}
        for number, seats, location in TABLES:
            if number not in tables:
                tables[number] = backend.create_table(number, seats, location)
                print("  + стол", tables[number])

        if backend.get_all_bookings():
            print("  бронирования уже есть — пропускаю")
        else:
            start = (datetime.now() + timedelta(days=1)).replace(
                hour=18, minute=0, second=0, microsecond=0
            )
            plan = [
                (USERS[0][1], 1, start, start + timedelta(hours=2)),
                (USERS[1][1], 2, start + timedelta(hours=1), start + timedelta(hours=3)),
            ]
            for phone, table_number, begin, end in plan:
                try:
                    booking = backend.create_booking(
                        users[phone].id, tables[table_number].id, begin, end
                    )
                    print("  + бронь", booking)
                except BookingError as exc:
                    print("  ! пропущено:", exc)

        print(
            "\nИтог: пользователей {0}, столов {1}, броней {2}".format(
                len(backend.get_all_users()),
                len(backend.get_all_tables()),
                len(backend.get_all_bookings()),
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
