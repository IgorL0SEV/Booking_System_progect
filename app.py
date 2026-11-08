"""CLI мини-системы бронирования.

Запуск:
    python app.py

Меню: пользователи, столы, бронирования и проверка доступности стола.
"""

from __future__ import annotations

import sys
from datetime import datetime

import psycopg2

from backend import BookingBackend, BookingError
from postgres_driver import readable_server_error

DATE_FORMATS = ("%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M", "%d.%m %H:%M")


def ask(prompt: str) -> str:
    return input(prompt).strip()


def ask_int(prompt: str) -> int:
    while True:
        raw = ask(prompt)
        try:
            return int(raw)
        except ValueError:
            print("  Нужно целое число.")


def ask_optional_int(prompt: str) -> int | None:
    while True:
        raw = ask(prompt)
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            print("  Нужно целое число или пустая строка.")


def ask_datetime(prompt: str, default: datetime | None = None) -> datetime:
    hint = f" [{default:%d.%m.%Y %H:%M}]" if default else " (ДД.ММ.ГГГГ ЧЧ:ММ)"
    while True:
        raw = ask(f"{prompt}{hint}: ")
        if not raw and default is not None:
            return default
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
        print("  Не понял дату. Пример: 12.11.2026 18:30")


def ask_optional_datetime(prompt: str) -> datetime | None:
    while True:
        raw = ask(f"{prompt} (Enter — без изменений): ")
        if not raw:
            return None
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
        print("  Не понял дату. Пример: 12.11.2026 18:30")


def print_line(title: str) -> None:
    print(f"\n{title}")
    print("-" * len(title))


# --- пользователи ----------------------------------------------------


def users_menu(backend: BookingBackend) -> None:
    while True:
        print_line("Пользователи")
        print("1. Список\n2. Добавить\n3. Изменить\n4. Удалить\n0. Назад")
        choice = ask("Выбор: ")
        try:
            if choice == "1":
                users = backend.get_all_users()
                if not users:
                    print("  Пользователей пока нет.")
                for user in users:
                    print("  ", user)
            elif choice == "2":
                user = backend.create_user(ask("Имя: "), ask("Телефон: "))
                print("  Создан:", user)
            elif choice == "3":
                user_id = ask_int("id пользователя: ")
                name = ask("Новое имя (Enter — без изменений): ") or None
                phone = ask("Новый телефон (Enter — без изменений): ") or None
                print("  Обновлён:", backend.update_user(user_id, name, phone))
            elif choice == "4":
                user_id = ask_int("id пользователя: ")
                removed = backend.delete_user(user_id)
                print("  Удалён." if removed else "  Не найден.")
            elif choice == "0":
                return
            else:
                print("  Нет такого пункта.")
        except BookingError as exc:
            print("  Ошибка:", exc)


# --- столы -----------------------------------------------------------


def tables_menu(backend: BookingBackend) -> None:
    while True:
        print_line("Столы")
        print("1. Список\n2. Добавить\n3. Изменить\n4. Удалить\n0. Назад")
        choice = ask("Выбор: ")
        try:
            if choice == "1":
                tables = backend.get_all_tables()
                if not tables:
                    print("  Столов пока нет.")
                for table in tables:
                    print("  ", table)
            elif choice == "2":
                table = backend.create_table(
                    ask_int("Номер стола: "),
                    ask_int("Мест: "),
                    ask("Расположение (Enter — не указывать): ") or None,
                )
                print("  Создан:", table)
            elif choice == "3":
                table_id = ask_int("id стола: ")
                number = ask_optional_int("Новый номер (Enter — без изменений): ")
                seats = ask_optional_int("Новых мест (Enter — без изменений): ")
                location = ask("Новое расположение (Enter — без изменений): ") or None
                print("  Обновлён:", backend.update_table(table_id, number, seats, location))
            elif choice == "4":
                table_id = ask_int("id стола: ")
                removed = backend.delete_table(table_id)
                print("  Удалён." if removed else "  Не найден.")
            elif choice == "0":
                return
            else:
                print("  Нет такого пункта.")
        except BookingError as exc:
            print("  Ошибка:", exc)


# --- бронирования ----------------------------------------------------


def bookings_menu(backend: BookingBackend) -> None:
    while True:
        print_line("Бронирования")
        print("1. Список\n2. Создать\n3. Изменить\n4. Удалить\n0. Назад")
        choice = ask("Выбор: ")
        try:
            if choice == "1":
                bookings = backend.get_all_bookings()
                if not bookings:
                    print("  Бронирований пока нет.")
                for booking in bookings:
                    print("  ", booking)
            elif choice == "2":
                booking = backend.create_booking(
                    ask_int("id пользователя: "),
                    ask_int("id стола: "),
                    ask_datetime("Начало"),
                    ask_datetime("Окончание"),
                )
                print("  Создано:", booking)
            elif choice == "3":
                booking_id = ask_int("id брони: ")
                user_id = ask_optional_int("Новый id пользователя (Enter — без изменений): ")
                table_id = ask_optional_int("Новый id стола (Enter — без изменений): ")
                start = ask_optional_datetime("Новое начало")
                end = ask_optional_datetime("Новое окончание")
                print(
                    "  Обновлено:",
                    backend.update_booking(booking_id, user_id, table_id, start, end),
                )
            elif choice == "4":
                booking_id = ask_int("id брони: ")
                removed = backend.delete_booking(booking_id)
                print("  Удалено." if removed else "  Не найдено.")
            elif choice == "0":
                return
            else:
                print("  Нет такого пункта.")
        except BookingError as exc:
            print("  Ошибка:", exc)


# --- проверка доступности -------------------------------------------


def availability_menu(backend: BookingBackend) -> None:
    print_line("Проверка доступности стола")
    try:
        table_id = ask_int("id стола: ")
        table = backend.get_table(table_id)
        if table is None:
            print("  Стол не найден.")
            return
        start = ask_datetime("Начало")
        end = ask_datetime("Окончание")
        free = backend.check_table_availability(table_id, start, end)
        print(f"\n  {table}")
        print(f"  Интервал: {start:%d.%m.%Y %H:%M}–{end:%H:%M}")
        print("  Результат:", "СТОЛ СВОБОДЕН" if free else "СТОЛ ЗАНЯТ")
    except BookingError as exc:
        print("  Ошибка:", exc)


def main() -> int:
    try:
        backend = BookingBackend.from_env()
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1

    try:
        with backend:
            backend.init_schema()
            print(f"Подключено к базе «{backend.driver.dbname}». Таблицы готовы.")
            while True:
                print("\n=== Мини-система бронирования ===")
                print("1. Пользователи")
                print("2. Столы")
                print("3. Бронирования")
                print("4. Проверить доступность стола")
                print("0. Выход")
                choice = ask("Выбор: ")
                if choice == "1":
                    users_menu(backend)
                elif choice == "2":
                    tables_menu(backend)
                elif choice == "3":
                    bookings_menu(backend)
                elif choice == "4":
                    availability_menu(backend)
                elif choice == "0":
                    print("До встречи.")
                    return 0
                else:
                    print("  Нет такого пункта.")
    except (KeyboardInterrupt, EOFError):
        print("\nВыход.")
        return 0
    except UnicodeDecodeError as exc:
        print("\nОшибка PostgreSQL:", readable_server_error(exc), file=sys.stderr)
        return 1
    except psycopg2.Error as exc:
        print("\nОшибка PostgreSQL:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
