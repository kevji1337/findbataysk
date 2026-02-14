# Скрипт для настройки локального окружения на Windows

Write-Host "🔧 Настройка локального окружения для FindBataysk" -ForegroundColor Cyan

# Шаг 1: Удалить старое venv (если есть)
if (Test-Path ".venv") {
    Write-Host "🗑️  Удаление старого виртуального окружения..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force .venv
}

# Шаг 2: Проверить Python
Write-Host "`n🐍 Проверка Python..." -ForegroundColor Cyan
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Python не найден! Установи Python 3.11+ с python.org" -ForegroundColor Red
    exit 1
}
Write-Host "✅ $pythonVersion" -ForegroundColor Green

# Шаг 3: Создать новое venv
Write-Host "`n📦 Создание виртуального окружения..." -ForegroundColor Cyan
python -m venv .venv
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Ошибка создания venv!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Виртуальное окружение создано" -ForegroundColor Green

# Шаг 4: Активировать venv
Write-Host "`n🔌 Активация виртуального окружения..." -ForegroundColor Cyan
& .\.venv\Scripts\Activate.ps1

# Шаг 5: Обновить pip
Write-Host "`n⬆️  Обновление pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

# Шаг 6: Установить зависимости
Write-Host "`n📚 Установка зависимостей из requirements.txt..." -ForegroundColor Cyan
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Ошибка установки зависимостей!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Зависимости установлены" -ForegroundColor Green

# Шаг 7: Проверка установки
Write-Host "`n🔍 Проверка установки..." -ForegroundColor Cyan
python -c "import aiogram; print(f'✅ aiogram {aiogram.__version__}')"
python -c "import sqlalchemy; print(f'✅ SQLAlchemy {sqlalchemy.__version__}')"
python -c "import asyncpg; print(f'✅ asyncpg установлен')"

Write-Host "`n✅ Готово! Виртуальное окружение настроено." -ForegroundColor Green
Write-Host "`n📝 Следующие шаги:" -ForegroundColor Cyan
Write-Host "   1. Убедись, что Docker запущен и БД работает: docker compose ps" -ForegroundColor White
Write-Host "   2. Обнови DATABASE_URL в .env на Postgres (если используешь Docker)" -ForegroundColor White
Write-Host "   3. Примени миграции: alembic upgrade head" -ForegroundColor White
Write-Host "   4. Проверь подключение: python scripts\check_db_connection.py" -ForegroundColor White
Write-Host "   5. Запусти бота: python -m bot.main" -ForegroundColor White
