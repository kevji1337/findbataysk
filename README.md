# 🤖 Menikov Alkash Bot

Telegram бот для реферальной программы и управления рекламой в канале.

## 🚀 Быстрый старт

### 1. Клонирование и настройка окружения

```bash
# Создать виртуальное окружение
python -m venv .venv

# Активировать (Windows)
.venv\Scripts\activate

# Активировать (Linux/Mac)
source .venv/bin/activate

# Установить зависимости
pip install -r requirements.txt
```

### 2. Настройка переменных окружения

```bash
# Скопировать пример конфига
cp .env.example .env

# Заполнить значения в .env
```

**Обязательные переменные:**
- `BOT_TOKEN` — токен бота от @BotFather
- `CHANNEL_ID` — ID канала (начинается с -100)
- `ADMIN_IDS` — Telegram ID админов (через запятую)

### 3. Настройка базы данных

#### Supabase Postgres через Docker

```bash
# Запустить Supabase Postgres
make docker-up
# или
docker-compose up -d db

# Применить миграции
make docker-migrate
# или
alembic upgrade head

# Проверить подключение
make docker-db-check
# или
python scripts/check_db_connection.py
```

Подробнее: см. [docker-setup.md](docker-setup.md)

### 4. Применить миграции базы данных

```bash
# Применить все миграции
alembic upgrade head

# Посмотреть текущую версию
alembic current

# Создать новую миграцию (при изменении моделей)
alembic revision --autogenerate -m "описание изменений"
```

### 5. Запуск

#### Локально (без Docker)

```bash
python -m bot.main
# или
make run
```

#### В Docker контейнере

```bash
# Собрать и запустить все сервисы
docker-compose up -d

# Просмотр логов
docker-compose logs -f bot
```

## 📁 Структура проекта

```
bot/
├── main.py              # Точка входа
├── config.py            # Конфигурация из .env
│
├── core/                # Бизнес-логика
│   ├── constants.py     # Константы (REFERRALS_PER_GIFT и т.д.)
│   └── referral_service.py  # Сервис расчёта подарков
│
├── database/
│   ├── models.py        # SQLAlchemy модели
│   ├── repository.py    # Репозитории для работы с БД
│   └── session.py       # Unit of Work для транзакций
│
├── storage/              # FSM Storage (Redis)
│
├── handlers/            # Обработчики команд и callback'ов
│   ├── start.py         # /start и главное меню
│   ├── referral.py      # Реферальная программа
│   ├── advertising.py   # Заявки на рекламу
│   ├── admin.py         # Админ-панель
│   └── admin_contact.py # Связь с администрацией
│
├── keyboards/
│   └── inline.py        # Inline-клавиатуры
│
├── middlewares/
│   └── rate_limit.py    # Rate limiting с LRU-кэшем
│
├── services/
│   └── admin_notify.py  # Уведомления админам
│
├── states/
│   └── advertising.py   # FSM состояния
│
└── media/
    └── welcome.jpg      # Приветственное фото (опционально)

migrations/              # Alembic миграции
├── env.py
├── script.py.mako
└── versions/
    └── 001_initial.py

scripts/                 # Вспомогательные скрипты
└── add_test_referrals.py

tests/                   # Тесты
├── test_core.py
└── test_config.py
```

## 🔧 Функционал

### Для пользователей:
- 🔗 **Реферальная программа** — персональные пригласительные ссылки
- 🎁 **Подарки за рефералов** — 1 мишка за каждые 5 приглашённых
- 📢 **Заявки на рекламу** — подача заявки на взаимопиар
- 📞 **Связь с администрацией**

### Для админов:
- 📊 **Статистика** — пользователи, ссылки, переходы
- 🏆 **Топ рефереров** — лидерборд по приглашениям
- 📋 **История заявок** — фильтрация по статусу
- ✅ **Модерация** — одобрение/отклонение заявок

## ⚙️ Конфигурация

### Несколько админов

```env
# Один админ
ADMIN_IDS=123456789

# Несколько админов
ADMIN_IDS=123456789,987654321,555555555
```

### Изменение награды за рефералов

Отредактируй `bot/core/constants.py`:

```python
REFERRALS_PER_GIFT = 5  # Изменить на нужное количество
```

## 🐳 Docker

### Быстрый старт с Supabase Postgres

```bash
# 1. Настрой .env (скопируй из .env.example)
cp .env.example .env

# 2. Запусти БД
make docker-up

# 3. Примени миграции
make docker-migrate

# 4. Проверь подключение
make docker-db-check

# 5. Запусти бота локально или в Docker
python -m bot.main  # локально
# или
docker-compose up -d  # в контейнере
```

**Полезные команды:**

```bash
make docker-up       # Запустить Supabase Postgres
make docker-down      # Остановить контейнеры
make docker-logs      # Просмотр логов
make docker-db-check  # Проверить подключение к БД
make docker-migrate   # Применить миграции
make docker-backup    # Создать бэкап БД
```

Подробная документация: [docker-setup.md](docker-setup.md)

## 🛠️ Разработка

### Запуск тестов

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=bot

# Конкретный файл
pytest tests/test_core.py -v
```

### Добавление тестовых рефералов

```bash
python scripts/add_test_referrals.py 5  # Добавить 5 рефералов
```

### Миграции БД

```bash
# Создать миграцию после изменения моделей
alembic revision --autogenerate -m "add new field"

# Применить миграции
alembic upgrade head

# Откатить последнюю миграцию
alembic downgrade -1
```

### Структура команд

- `/start` — Главное меню
- `/admin` — Админ-панель (только для админов)

## 🏗️ Архитектура

### FSM Storage
Состояния FSM хранятся в Redis (`REDIS_URL`). Это означает, что:
- Состояния сохраняются между перезапусками бота
- Пользователь не потеряет прогресс при падении бота
- Требуется работающий экземпляр Redis

### Rate Limiting
Middleware с LRU-кэшем (макс. 10000 пользователей):
- Защита от флуда
- Автоматическая очистка старых записей
- Нет утечек памяти

### Миграции (Alembic)
- Все изменения схемы БД версионируются
- Поддержка отката миграций
- Автогенерация из моделей SQLAlchemy

## 📄 Лицензия

MIT

## Runtime Changes (2026-02)

- FSM storage moved from local SQLite to Redis (`REDIS_URL` is required).
- Admin broadcast is now queued to background jobs with persisted progress in DB (`broadcast_jobs`).
- Advertising approve/reject callbacks now carry only `request_id`; user is resolved from DB.

### Bootstrap (Windows)

```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1
```

### Python version

Project uses Python `3.11` (see `.python-version` and `pyproject.toml`).
Use only `.venv` in this repository.

## Operational Documentation

- Git history and deployment pipeline: `docs/GIT_DEPLOY_PIPELINE.md`
- Production operations (monitoring/logging/backups): `docs/PROD_OPERATIONS.md`
- Reward claims policy and admin SLA: `docs/REWARD_POLICY_SLA.md`

## GitHub Actions

- CI workflow: `.github/workflows/ci.yml`
- Production deploy workflow: `.github/workflows/deploy.yml`

## Ops Configs

- Prometheus: `ops/monitoring/prometheus.yml`
- Promtail: `ops/logging/promtail-config.yml`
- Backup scripts: `ops/backup/backup-postgres.sh`, `ops/backup/restore-postgres.sh`
- Windows backup helper: `scripts/backup_postgres.ps1`
- Load testing guide: `docs/LOAD_TESTING.md`
