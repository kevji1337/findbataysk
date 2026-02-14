# 🚀 Деплой на VPS

## Требования к VPS

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
| `POSTGRES_PASSWORD` | Придумать сложный пароль |

### 4. Запустить

```bash
docker compose up -d
```

Готово! Бот:
1. Поднимет PostgreSQL
2. Поднимет Redis
3. Дождётся готовности БД
4. Применит миграции
5. Запустится

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

### Миграции падают
```bash
# Посмотреть ошибку
docker compose logs bot | grep -A5 "migrations"

# Зайти в контейнер вручную
docker compose exec bot bash
alembic current
alembic upgrade head
```

### БД не запускается
```bash
docker compose logs db
```
Проверь: хватает ли места на диске (`df -h`).
