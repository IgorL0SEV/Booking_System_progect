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

## Запуск на другой машине (после `git clone`)

`venv`, `.env` и сама база в git не хранятся — на новой машине их нужно создать.
Порядок важен: сначала база, потом таблицы.

```powershell
# 1. Проверить, что сервер этой машины работает
Get-Service -Name '*postgres*'
Test-NetConnection localhost -Port 5432

# 2. Окружение и зависимости
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. Свой .env (пароль ЭТОЙ установки PostgreSQL)
Copy-Item .env.example .env
notepad .env

# 4. Создать базу booking
python ensure_database.py

# 5. Создать таблицы и демо-данные
python app.py          # при старте создаёт users, tables, bookings и индексы
python seed_demo.py    # 3 пользователя, 3 стола, 2 брони (идемпотентно)
```

Почему два шага: `CREATE DATABASE` нельзя выполнить из подключения к самой создаваемой
базе, поэтому `ensure_database.py` подключается к служебной `postgres`. Если базы нет,
`app.py` завершится ошибкой `3D000` — тогда сначала шаг 4.

`ensure_database.py` и `seed_demo.py` можно запускать повторно: существующую базу и
записи они не дублируют.

Ожидаемый результат после шага 5:

```text
Итог: пользователей 3, столов 3, броней 2
```

### Пересоздать базу с нуля

Если база испорчена или нужна чистая:

```powershell
# 1. Удалить базу (активные подключения pgAdmin должны быть закрыты)
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres `
    -c "DROP DATABASE booking WITH (FORCE);"

# 2. Создать заново и наполнить
python ensure_database.py
python seed_demo.py
```

То же мышкой в pgAdmin: правый клик по базе `booking` → *Delete/Drop* → подтвердить,
затем снова `python ensure_database.py` и `python seed_demo.py`.

`WITH (FORCE)` есть с PostgreSQL 13: он отключает активные сессии. На более старых
версиях сначала закройте вкладки с базой в pgAdmin.

### Сбросить только данные, не удаляя базу

```sql
TRUNCATE bookings, tables, users RESTART IDENTITY CASCADE;
```

`RESTART IDENTITY` начинает нумерацию `id` заново, `CASCADE` учитывает внешние ключи.
После этого можно запустить `python seed_demo.py`.

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
