"""Проверка CRUD и правил бронирования на живой базе.

Запуск: python smoke_test.py
Создаёт временные записи и удаляет их в конце; демо-данные не трогает.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from backend import BookingBackend, BookingConflict, BookingError

ok = 0
fail = 0


def check(label: str, condition: bool) -> None:
    global ok, fail
    if condition:
        ok += 1
        print(f"  OK   {label}")
    else:
        fail += 1
        print(f"  FAIL {label}")


def main() -> int:
    with BookingBackend.from_env() as backend:
        backend.init_schema()

        print("=== Пользователи: CRUD ===")
        user = backend.create_user("Тест Пользователь", "+7 999 000-00-01")
        check("create_user", user.id > 0 and user.name == "Тест Пользователь")

        duplicate = False
        try:
            backend.create_user("Дубль", "+7 999 000-00-01")
        except BookingError:
            duplicate = True
        check("уникальный телефон проверяется", duplicate)

        updated = backend.update_user(user.id, name="Тест Обновлён")
        check("update_user", updated.name == "Тест Обновлён")
        check("get_user", backend.get_user(user.id) == updated)
        check("get_all_users", any(u.id == user.id for u in backend.get_all_users()))

        print("=== Столы: CRUD ===")
        table = backend.create_table(99, 4, "тест-зал")
        check("create_table", table.number == 99 and table.seats == 4)
        table_updated = backend.update_table(table.id, seats=6)
        check("update_table", table_updated.seats == 6)
        check("get_all_tables", any(t.id == table.id for t in backend.get_all_tables()))

        print("=== Бронирования и проверка пересечений ===")
        base = (datetime.now() + timedelta(days=3)).replace(
            hour=12, minute=0, second=0, microsecond=0
        )
        booking = backend.create_booking(
            user.id, table.id, base, base + timedelta(hours=2)
        )
        check("create_booking", booking.id > 0)
        check(
            "свободный интервал (после брони)",
            backend.check_table_availability(
                table.id, base + timedelta(hours=3), base + timedelta(hours=4)
            ),
        )
        check(
            "занятый интервал (середина брони)",
            not backend.check_table_availability(
                table.id, base + timedelta(hours=1), base + timedelta(hours=3)
            ),
        )
        check(
            "стык интервалов разрешён (конец = начало)",
            backend.check_table_availability(
                table.id, base + timedelta(hours=2), base + timedelta(hours=4)
            ),
        )

        conflict = False
        try:
            backend.create_booking(
                user.id, table.id, base + timedelta(minutes=30), base + timedelta(hours=1)
            )
        except BookingConflict:
            conflict = True
        check("пересечение отклонено при создании", conflict)

        extended = backend.update_booking(booking.id, end_time=base + timedelta(hours=3))
        check("update_booking", extended.end_time == base + timedelta(hours=3))

        second = backend.create_booking(
            user.id, table.id, base + timedelta(hours=5), base + timedelta(hours=6)
        )
        conflict_on_update = False
        try:
            backend.update_booking(second.id, start_time=base + timedelta(hours=1))
        except BookingConflict:
            conflict_on_update = True
        check("пересечение отклонено при обновлении", conflict_on_update)

        invalid = False
        try:
            backend.create_booking(user.id, table.id, base, base)
        except BookingError:
            invalid = True
        check("интервал с нулевой длительностью отклонён", invalid)

        check("get_all_bookings содержит бронь", any(b.id == booking.id for b in backend.get_all_bookings()))
        check("delete_booking", backend.delete_booking(booking.id) and backend.delete_booking(second.id))
        check("delete_table", backend.delete_table(table.id))
        check("delete_user", backend.delete_user(user.id))

        print(f"\nИтого: OK {ok}, FAIL {fail}")
        return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
