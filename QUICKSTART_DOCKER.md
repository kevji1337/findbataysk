# 🚀 Быстрый старт с Docker + Supabase

## За 3 шага

### 1️⃣ Настройка окружения

```bash
# Скопируй .env.example в .env
cp .env.example .env

# Отредактируй .env и заполни:
# - BOT_TOKEN (от @BotFather)
# - CHANNEL_ID (ID канала)
# - ADMIN_IDS (твой Telegram ID)
# - POSTGRES_PASSWORD (или оставь postgres для локальной разработки)
```

### 2️⃣ Запуск Supabase Postgres

```bash
# Запустить только БД
make docker-up

# Или вручную:
docker-compose up -d db
```

### 3️⃣ Применение миграций и запуск

```bash
# Применить миграции
make docker-migrate

# Проверить подключение
make docker-db-check

# Запустить бота локально (подключится к БД в Docker)
python -m bot.main
```

## ✅ Готово!

Бот работает локально, но использует Supabase Postgres из Docker контейнера.

## 📋 Что дальше?

- **Просмотр логов БД:** `docker-compose logs -f db`
- **Подключиться к БД:** `docker exec -it findbataysk_db psql -U postgres`
- **Остановить БД:** `make docker-down`
- **Бэкап БД:** `make docker-backup`

Подробнее: [docker-setup.md](docker-setup.md)
