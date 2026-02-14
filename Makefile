# Makefile для удобства разработки
# Использование: make <команда>

.PHONY: run dev install bootstrap test lint clean help docker-up docker-down docker-logs docker-db-check docker-migrate

# Запуск бота
run:
	python -m bot.main

# Установка зависимостей
install:
	pip install -r requirements-dev.txt

# Bootstrap локального окружения (Windows PowerShell)
bootstrap:
	powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1

# Добавить тестовых рефералов
test-refs:
	python scripts/add_test_referrals.py 5

# Очистка кэша Python
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Docker команды
docker-up:
	docker-compose up -d db
	@echo "База данных запущена. Примените миграции: make docker-migrate"

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-db-check:
	python scripts/check_db_connection.py

docker-migrate:
	alembic upgrade head

docker-backup:
	@echo "Создание бэкапа БД..."
	docker exec findbataysk_db pg_dump -U postgres postgres > backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Бэкап создан"

# Помощь
help:
	@echo "Доступные команды:"
	@echo "  make run            - Запустить бота"
	@echo "  make install        - Установить зависимости"
	@echo "  make test-refs      - Добавить 5 тестовых рефералов"
	@echo "  make clean          - Очистить кэш Python"
	@echo ""
	@echo "Docker команды:"
	@echo "  make docker-up      - Запустить Supabase Postgres"
	@echo "  make docker-down    - Остановить контейнеры"
	@echo "  make docker-logs    - Просмотр логов"
	@echo "  make docker-db-check - Проверить подключение к БД"
	@echo "  make docker-migrate - Применить миграции"
	@echo "  make docker-backup  - Создать бэкап БД"

backup-db:
	bash ops/backup/backup-postgres.sh

backup-db-win:
	powershell -ExecutionPolicy Bypass -File scripts/backup_postgres.ps1

loadtest-menu:
	locust -f loadtests/locustfile.py --headless -u 150 -r 50 -t 2m --csv loadtest_menu

loadtest-menu-py:
	python -m locust -f loadtests/locustfile.py --headless -u 150 -r 50 -t 2m --csv loadtest_menu
