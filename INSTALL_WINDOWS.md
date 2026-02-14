# Установка на Windows - Решение проблем

## Проблема: asyncpg не компилируется

Если при установке `asyncpg` возникает ошибка компиляции C-кода, это значит, что у тебя Python 3.14, а `asyncpg` ещё не поддерживает его полностью.

## Решение 1: Использовать Python 3.11 или 3.12 (рекомендуется)

### Шаг 1: Установить Python 3.11 или 3.12

1. Скачай Python 3.11 или 3.12 с официального сайта:
   - https://www.python.org/downloads/
   - Выбери версию **3.11.x** или **3.12.x** (не 3.14!)

2. При установке **обязательно отметь галочку "Add Python to PATH"**

3. После установки перезапусти PowerShell

### Шаг 2: Проверить версию Python

```powershell
python --version
# Должно быть: Python 3.11.x или Python 3.12.x
```

### Шаг 3: Пересоздать venv с правильной версией

```powershell
# Удалить старое venv
Remove-Item -Recurse -Force .venv -ErrorAction SilentlyContinue

# Создать новое с правильной версией Python
python -m venv .venv

# Активировать
.\.venv\Scripts\Activate.ps1

# Установить зависимости
pip install --upgrade pip
pip install -r requirements.txt
```

## Решение 2: Использовать только binary wheels (если доступны)

Попробуй установить только предкомпилированные пакеты:

```powershell
pip install --only-binary :all: -r requirements.txt
```

Если это не сработает, используй **Решение 1** (Python 3.11/3.12).

## Решение 3: Установить Visual C++ Build Tools (если хочешь компилировать)

Если хочешь компилировать C-расширения на Windows:

1. Скачай и установи **Microsoft C++ Build Tools**:
   - https://visualstudio.microsoft.com/visual-cpp-build-tools/
   - При установке выбери "Desktop development with C++"

2. После установки перезапусти PowerShell и попробуй снова:

```powershell
pip install -r requirements.txt
```

Но это долго и сложно. **Лучше использовать Python 3.11/3.12** (Решение 1).

## Проверка после установки

После успешной установки проверь:

```powershell
python -c "import asyncpg; print(f'✅ asyncpg {asyncpg.__version__} установлен')"
python -c "import aiogram; print(f'✅ aiogram {aiogram.__version__} установлен')"
```

## Если ничего не помогает

Используй Docker для запуска всего окружения (включая Python):

```powershell
# Запустить всё в Docker
docker-compose up -d
```

Тогда не нужно устанавливать Python локально.
