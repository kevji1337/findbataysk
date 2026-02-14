# Docker Setup для FindBataysk

Инструкция по развертыванию локальной базы данных Supabase (self-hosted) через Docker.

## Требования

- Docker и Docker Compose установлены
- Python 3.11+ (для локальной разработки без Docker)

## Быстрый старт

### 1. Настройка переменных окружения

Скопируйте `.env.example` в `.env` и заполните значения:

```bash
cp .env.example .env
```

Отредактируйте `.env`:
```bash
BOT_TOKEN=your_bot_token_from_botfather
CHANNEL_ID=-100xxxxxxxxxx
ADMIN_IDS=your_telegram_user_id
POSTGRES_PASSWORD=postgres  # или свой безопасный пароль
```

### 2. Запуск Supabase Postgres

Запустите только базу данных:

```bash
docker-compose up -d db
```

Проверьте, что контейнер запущен:

```bash
docker-compose ps
```

Подключитесь к БД (опционально, для проверки):

```bash
docker exec -it findbataysk_db psql -U postgres
```

### 3. Применение миграций

Примените миграции Alembic к новой БД:

```bash
# Убедитесь, что DATABASE_URL указывает на контейнер
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/postgres

# Примените миграции
alembic upgrade head
```

Или через Docker (если бот уже в контейнере):

```bash
docker-compose exec bot alembic upgrade head
```

### 4. Запуск бота (опционально)

#### Вариант A: Локально (без Docker)

```bash
# Убедитесь, что DATABASE_URL указывает на контейнер
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/postgres

# Запустите бота
python -m bot.main
```

#### Вариант B: В Docker контейнере

```bash
# Соберите образ
docker-compose build bot

# Запустите все сервисы
docker-compose up -d

# Просмотр логов
docker-compose logs -f bot
```

## Структура контейнеров

- **`db`** — Supabase Postgres 15.1.0.147
  - Порт: `5432` (по умолчанию)
  - Данные сохраняются в volume `postgres_data`
  - Healthcheck проверяет готовность БД

- **`bot`** — Telegram бот
  - Зависит от `db` (ждёт healthcheck)
  - Автоматически подключается к БД через Docker network
  - FSM storage (SQLite) монтируется как volume

## Полезные команды

### Остановка

```bash
# Остановить все контейнеры
docker-compose down

# Остановить и удалить volumes (⚠️ удалит данные БД!)
docker-compose down -v
```

### Просмотр логов

```bash
# Все сервисы
docker-compose logs -f

# Только бот
docker-compose logs -f bot

# Только БД
docker-compose logs -f db
```

### Бэкап БД

```bash
# Создать бэкап
docker exec findbataysk_db pg_dump -U postgres postgres > backup_$(date +%Y%m%d_%H%M%S).sql

# Восстановить из бэкапа
docker exec -i findbataysk_db psql -U postgres postgres < backup_YYYYMMDD_HHMMSS.sql
```

### Подключение к БД

```bash
# Через psql внутри контейнера
docker exec -it findbataysk_db psql -U postgres

# Или через внешний клиент
psql -h localhost -p 5432 -U postgres -d postgres
```

## Миграция данных из существующей БД

Если у вас уже есть данные в SQLite или другой Postgres:

### Из SQLite

1. Экспортируйте данные из SQLite (используйте скрипт или SQLite Browser)
2. Импортируйте в Postgres через `psql` или скрипт миграции

### Из другой Postgres

```bash
# Экспорт из старой БД
pg_dump -h old_host -U old_user old_db > dump.sql

# Импорт в новую БД (в контейнере)
docker exec -i findbataysk_db psql -U postgres postgres < dump.sql
```

## Troubleshooting

### БД не запускается

```bash
# Проверьте логи
docker-compose logs db

# Проверьте, не занят ли порт 5432
netstat -an | grep 5432  # Linux/Mac
netstat -ano | findstr 5432  # Windows
```

### Бот не подключается к БД

1. Убедитесь, что `db` контейнер запущен: `docker-compose ps`
2. Проверьте `DATABASE_URL` в `.env` или `docker-compose.yml`
3. Проверьте логи бота: `docker-compose logs bot`

### Миграции не применяются

```bash
# Проверьте текущую версию
alembic current

# Просмотрите историю миграций
alembic history

# Примените вручную
alembic upgrade head
```

## Production рекомендации

Для продакшена:

1. **Измените пароль БД** на безопасный в `.env` и `docker-compose.yml`
2. **Используйте secrets** вместо plain-text паролей в `.env`
3. **Настройте регулярные бэкапы** (cron job или CI/CD)
4. **Мониторинг** — добавьте healthcheck endpoints и логирование
5. **Ограничьте доступ** к порту 5432 только для localhost или используйте firewall

## Дополнительно

- [Supabase Self-Hosting Docs](https://supabase.com/docs/guides/self-hosting)
- [Docker Compose Docs](https://docs.docker.com/compose/)
- [Alembic Migrations](https://alembic.sqlalchemy.org/)
