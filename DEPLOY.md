# 🚀 Деплой

## Coolify

### Что создать

В Coolify нужны:
- `Application` из этого репозитория
- `PostgreSQL` сервис
- `Redis` сервис

### Build / Start

- Тип: `Dockerfile`
- Dockerfile path: `./Dockerfile`
- Port: `8080`

Стартовая команда отдельно не нужна: контейнер использует `entrypoint.sh`.

### Переменные окружения приложения

Обязательные:

| Переменная | Пример |
|------------|--------|
| `BOT_TOKEN` | `123456:AA...` |
| `CHANNEL_ID` | `-1001234567890` |
| `ADMIN_IDS` | `123456789,987654321` |
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@postgres:5432/dbname` |
| `REDIS_URL` | `redis://redis:6379/0` |

Опциональные:

| Переменная | Значение по умолчанию |
|------------|------------------------|
| `REDIS_PASSWORD` | пусто |
| `PORT` | `8080` |
| `DROP_PENDING_UPDATES_ON_STARTUP` | `false` |

### Проверка после деплоя

- В логах должно быть: `Database is ready`
- Затем: `Running migrations`
- Затем: `Starting bot`

## Ручной деплой на VPS

### Требования к VPS

- Ubuntu 22.04+ (или любой Linux с Docker)
- Docker + Docker Compose
- Git
- Минимум 1 GB RAM, 10 GB disk

## Первый деплой

### 1. Установить Docker (если ещё нет)

```bash
# Установить Docker
curl -fsSL https://get.docker.com | sh

# Добавить пользователя в группу docker (чтобы не писать sudo)
sudo usermod -aG docker $USER

# Перезайти в сессию
exit
# подключиться заново по SSH
```

### 2. Склонировать репозиторий

```bash
cd /opt  # или любая другая директория
git clone <url> findbataysk
cd findbataysk
```

### 3. Настроить `.env`

```bash
cp .env.example .env
nano .env
```

Заполнить **обязательные** поля:

| Переменная | Откуда взять |
|------------|------------|
| `BOT_TOKEN` | @BotFather → `/newbot` |
| `CHANNEL_ID` | Переслать пост из канала боту @userinfobot |
| `ADMIN_IDS` | Отправить `/start` боту @userinfobot |
| `DATABASE_URL` | Строка подключения к внешнему Postgres |
| `REDIS_URL` | Строка подключения к Redis |

### 4. Запустить

```bash
docker compose up -d
```

Готово! Бот:
1. Поднимет Redis
2. Дождётся готовности БД
3. Применит миграции
4. Запустится

### 5. Проверить

```bash
# Логи бота
docker compose logs -f bot

# Статус контейнеров
docker compose ps
```

## Обновление

```bash
cd /opt/findbataysk

# Забрать изменения
git pull

# Пересобрать и перезапустить
docker compose up -d --build
```

Бот автоматически:
- Остановится
- Пересоберёт образ
- Применит новые миграции (если есть)
- Запустится

## Бэкап базы данных

```bash
# Создать бэкап
docker compose exec db pg_dump -U postgres postgres > backup_$(date +%Y%m%d_%H%M%S).sql

# Восстановить из бэкапа
cat backup.sql | docker compose exec -T db psql -U postgres postgres
```

## Полезные команды

```bash
# Перезапустить бота (без пересборки)
docker compose restart bot

# Остановить всё
docker compose down

# Остановить + удалить данные БД (ОСТОРОЖНО!)
docker compose down -v

# Посмотреть использование ресурсов
docker stats
```

## Troubleshooting


### Бот не запускается
```bash
docker compose logs bot
```
Проверь:
- Правильный ли `BOT_TOKEN`?
- Бот добавлен как админ в канал?
- `CHANNEL_ID` начинается с `-100`?

### БД не запускается
Проверьте строку подключения и доступность Postgres:
```bash
docker compose logs db
```

## 🔐 Безопасность

**Критически важно:**
1. Никогда не коммитить `.env` файл.
2. Регулярно обновлять `BOT_TOKEN` через @BotFather, если есть подозрение на утечку.
3. Использовать отдельные учётные данные для Postgres и Redis.
4. Бэкапы базы данных хранить в безопасном месте, не в web-root.

