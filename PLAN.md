# PLAN — мини-система бронирования (VPc07)

**Статус:** выполнено (базовый + средний уровень) · **Зафиксировано:** 2026-11-08
**Машина:** настольный ПК, Windows 11, PostgreSQL 18 локально

## Цель проекта

По бизнес-кейсу «мини-система бронирования» спроектировать три сущности, реализовать
полный CRUD, проверку пересекающихся броней по одному столу и CLI-интерфейс.

## Текущее состояние

| Блок | Статус |
|---|---|
| Схема `users`, `tables`, `bookings` | ✅ DDL в `postgres_driver.py` |
| Автосоздание таблиц из кода | ✅ `create_tables()` + индексы |
| Подключение через `.env` | ✅ `PostgresDriver.from_env()`, понятная ошибка при пропуске переменных |
| Минимальный CRUD | ✅ `create_user`, `create_table`, `create_booking`, `get_all_bookings` |
| Полный CRUD для трёх моделей | ✅ create / read / update / delete в `backend.py` |
| Проверка пересечений | ✅ `check_table_availability`, запрет при создании и обновлении |
| CLI-меню | ✅ `app.py`, пункт «Проверить доступность стола» |
| Демо-данные | ✅ 3 пользователя, 3 стола, 2 брони (`seed_demo.py`) |
| Проверка | ✅ `smoke_test.py`: 20/20 |
| Документация | ✅ README, конспект, справочник, самопроверка |

## Результат проверки (2026-11-08)

- `python smoke_test.py` → `Итого: OK 20, FAIL 0`:
  CRUD трёх моделей, уникальность телефона, свободный/занятый интервал, стык интервалов,
  отклонение пересечения при создании и при обновлении, нулевой интервал.
- `python seed_demo.py` → 3 пользователя, 3 стола, 2 брони; повторный запуск не дублирует.
- CLI: список пользователей, список броней, проверка доступности — вывод корректен.

## Предусловия на каждой машине

```powershell
Get-Service -Name '*postgres*'
Test-NetConnection localhost -Port 5432
python --version
```

## Продолжение на другой машине

```powershell
git clone https://github.com/IgorL0SEV/Booking_System_progect.git
cd Booking_System_progect
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env      # вписать пароль ЭТОЙ машины
notepad .env
python ensure_database.py
python seed_demo.py
python app.py
```

Ожидаемый результат: база `booking`, три пользователя, три стола, две брони.

## Что НЕ хранится в git

| Файл | Почему | Как восстановить |
|---|---|---|
| `.env` | реальный пароль | скопировать `.env.example` и вписать пароль |
| `venv/` | привязан к машине | `python -m venv venv` + `pip install -r requirements.txt` |
| `__pycache__/` | байткод | создаётся автоматически |

## Риски и заметки

- Пароль `postgres` помнит только человек; на каждой машине он свой.
- Проверка пересечений выполняется в приложении. На уровне БД её можно усилить
  ограничением `EXCLUDE USING gist` (требуется расширение `btree_gist`) — не сделано,
  чтобы не усложнять учебный проект.
- Время хранится без часового пояса (`TIMESTAMP`). Для нескольких часовых поясов нужен
  `TIMESTAMPTZ`.
- pgAdmin на машине идёт в комплекте с PostgreSQL 18
  (`C:\Program Files\PostgreSQL\18\pgAdmin 4\runtime\pgAdmin4.exe`).
