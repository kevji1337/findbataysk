-- Инициализация расширений PostgreSQL для Supabase
-- Этот файл выполнится автоматически при первом запуске контейнера

-- UUID extension (если понадобится в будущем)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- pgcrypto для хеширования (если понадобится)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Для полнотекстового поиска (опционально)
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
