-- server/migrations/init.sql
-- Выполняется автоматически при первом запуске Docker

-- Включаем расширения
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Функция для очистки FREE пользователей
CREATE OR REPLACE FUNCTION cleanup_free_user_data()
RETURNS TRIGGER AS $$
BEGIN
    IF (SELECT user_type FROM users WHERE id = NEW.user_id) = 'free' THEN
        DELETE FROM sensor_vectors sv_old
        WHERE sv_old.user_id = NEW.user_id
          AND sv_old.device_id = NEW.device_id
          AND sv_old.id NOT IN (
              SELECT id FROM (
                  SELECT id FROM sensor_vectors
                  WHERE user_id = NEW.user_id
                    AND device_id = NEW.device_id
                  ORDER BY timestamp DESC
                  LIMIT 30
              ) AS recent
          );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггер будет создан ПОСЛЕ создания таблицы sensor_vectors
-- Это делается в миграции Alembic (см. ниже)