# Справочник: схема и SQL мини-системы бронирования

## 1. Схема

```sql
CREATE TABLE IF NOT EXISTS users (
    id         SERIAL PRIMARY KEY,
    name       TEXT NOT NULL,
    phone      TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tables (
    id       SERIAL PRIMARY KEY,
    number   INT NOT NULL UNIQUE CHECK (number > 0),
    seats    INT NOT NULL CHECK (seats >= 1),
    location TEXT
);

CREATE TABLE IF NOT EXISTS bookings (
    id         SERIAL PRIMARY KEY,
    user_id    INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    table_id   INT NOT NULL REFERENCES tables(id) ON DELETE CASCADE,
    start_time TIMESTAMP NOT NULL,
    end_time   TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT booking_time_valid CHECK (end_time > start_time)
);

CREATE INDEX IF NOT EXISTS idx_bookings_table_time
    ON bookings (table_id, start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings (user_id);
```

## 2. Основные запросы

Список броней с именами и номерами столов:

```sql
SELECT b.id, b.user_id, b.table_id, b.start_time, b.end_time,
       u.name, t.number, b.created_at
FROM bookings b
JOIN users u ON u.id = b.user_id
JOIN tables t ON t.id = b.table_id
ORDER BY b.start_time, b.id;
```

Проверка пересечения:

```sql
SELECT COUNT(*)
FROM bookings
WHERE table_id = %s
  AND id <> %s              -- -1 при создании, id самой брони при обновлении
  AND start_time < %s       -- конец нового интервала
  AND end_time   > %s;      -- начало нового интервала
```

Свободен, если `COUNT(*) = 0`.

Создание с возвратом идентификатора:

```sql
INSERT INTO bookings (user_id, table_id, start_time, end_time)
VALUES (%s, %s, %s, %s) RETURNING id;
```

Удаление пользователя вместе с его бронями:

```sql
DELETE FROM users WHERE id = %s;   -- bookings уйдут по ON DELETE CASCADE
```

## 3. Математика интервалов

Полуинтервал `[start, end)`: начало включается, конец — нет. Отсюда:

- `10:00–12:00` и `12:00–14:00` — **не** пересекаются (стык);
- `11:00–13:00` и `12:00–14:00` — пересекаются;
- `13:00–15:00` и `12:00–14:00` — пересекаются.

Условие пересечения: `a.start < b.end AND a.end > b.start`.

## 4. Коды ошибок PostgreSQL

| Код | Имя | Когда |
|---|---|---|
| `23505` | `unique_violation` | дубликат телефона или номера стола |
| `23503` | `foreign_key_violation` | ссылка на несуществующего пользователя/стол |
| `23514` | `check_violation` | `end_time <= start_time`, `seats < 1` |
| `42601` | `syntax_error` | например, имя таблицы передали через `%s` |
| `28P01` | `invalid_password` | неверный пароль в `.env` |
| `3D000` | `invalid_catalog_name` | базы нет — запустить `ensure_database.py` |

## 5. Даты и время в Python

```python
from datetime import datetime, timedelta

start = datetime(2026, 11, 12, 18, 0)
end = start + timedelta(hours=2)      # 20:00
```

В `psycopg2` `datetime` передаётся как параметр `%s` без преобразований.
Обратно из `TIMESTAMP` приходит `datetime` без часового пояса.

Форматы ввода в CLI: `12.11.2026 18:30`, `2026-11-12 18:30`, `12.11 18:30`.

## 6. Полезные команды psql

```sql
\dt                          -- список таблиц
\d bookings                  -- структура и индексы
SELECT * FROM bookings ORDER BY start_time DESC LIMIT 10;
SELECT t.number, COUNT(b.id) AS bookings
FROM tables t LEFT JOIN bookings b ON b.table_id = t.id
GROUP BY t.number ORDER BY t.number;
```
