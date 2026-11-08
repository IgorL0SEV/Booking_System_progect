# Booking_System_progect — мини-система бронирования

**Курс:** «Профессия вайб-кодер», Модуль 4. Базы данных, VPc07
**СУБД:** PostgreSQL 18 · **Клиент:** psycopg2 + python-dotenv · **Интерфейс:** CLI

**Статус:** ✅ базовый + средний уровень выполнены и проверены на живой базе.

## Что осваиваем

- проектирование схемы под бизнес-задачу: `User`, `Table`, `Booking`;
- автосоздание таблиц из кода (`CREATE TABLE IF NOT EXISTS`);
- полный CRUD для трёх моделей через слой бизнес-логики;
- проверка пересекающихся бронирований по одному столу;
- CLI-меню для работы с пользователями, столами и бронями.

## Материалы

| Файл | Что внутри |
|---|---|
| [CONSPECT.md](CONSPECT.md) | Конспект проекта: схема, слои, логика пересечений, разбор кода |
| [PLAN.md](PLAN.md) | План по шагам, статус, проверка, продолжение на другой машине |
| [SAMOPROVERKA.md](SAMOPROVERKA.md) | 15 вопросов с ответами (ответы под раскрывающимися блоками) |
| [reference/booking-schema.md](reference/booking-schema.md) | Справочник: DDL, SQL-запросы, коды ошибок |

## Структура

```text
Booking_System_progect/
├── postgres_driver.py     # соединение, DDL, низкоуровневые запросы
├── backend.py             # бизнес-логика: полный CRUD + проверка доступности
├── models/                # модели данных
│   ├── user.py
│   ├── table.py
│   └── booking.py
├── app.py                 # CLI-меню
├── ensure_database.py     # создаёт базу booking, если её нет
├── seed_demo.py           # демо-данные: 3 пользователя, 3 стола, 2 брони
├── smoke_test.py          # 20 проверок CRUD и правил бронирования
├── requirements.txt
├── .env.example           # шаблон без секретов
└── .gitignore             # .env, venv/, __pycache__/
```

## Быстрый старт

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env                  # вписать пароль пользователя postgres

python ensure_database.py     # создать базу booking
python seed_demo.py           # демо-данные
python app.py                 # CLI-меню
```

Проверка правил без интерактивного меню:

```powershell
python smoke_test.py          # ожидается «Итого: OK 20, FAIL 0»
```

## Схема базы

```text
users (id, name, phone UNIQUE, created_at)
tables (id, number UNIQUE, seats, location)
bookings (id, user_id → users, table_id → tables, start_time, end_time, created_at)
```

- `bookings.user_id` и `bookings.table_id` — внешние ключи с `ON DELETE CASCADE`;
- `CHECK (end_time > start_time)` — запрет нулевого и отрицательного интервала;
- индекс `(table_id, start_time, end_time)` — ускоряет проверку пересечений.

## Правило доступности

Стол свободен в интервале `[start, end)`, если нет брони на этот стол, у которой:

```text
existed.start_time < new.end_time  AND  existed.end_time > new.start_time
```

Соседние интервалы (конец одной брони = начало следующей) не считаются пересечением.

## Что показывает CLI

```text
=== Мини-система бронирования ===
1. Пользователи
2. Столы
3. Бронирования
4. Проверить доступность стола
0. Выход
```

Пункт 4 — обязательная по заданию команда «Проверить доступность»: выбирается стол и
интервал, печатается `СТОЛ СВОБОДЕН` или `СТОЛ ЗАНЯТ`.

## Скриншоты для сдачи

1. Таблицы `users`, `tables`, `bookings` в pgAdmin.
2. Список бронирований (`3. Бронирования → 1. Список`).
3. Пункт `4. Проверить доступность стола` с результатом.

## Заметки

- `.env` и `venv/` в репозиторий не попадают — пароль у каждой машины свой.
- На Windows сообщения сервера могут приходить в cp1251; в драйвере это обходит
  `readable_server_error()`.
- Время хранится как `TIMESTAMP` без часового пояса — для учебного проекта достаточно.
