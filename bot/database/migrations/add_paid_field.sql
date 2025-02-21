-- Добавляем поле paid в таблицу users
ALTER TABLE users ADD COLUMN IF NOT EXISTS paid BOOLEAN DEFAULT FALSE;

-- Обновляем существующих пользователей, у которых были платежи
UPDATE users 
SET paid = TRUE 
WHERE id IN (
    SELECT DISTINCT user 
    FROM payments
);
