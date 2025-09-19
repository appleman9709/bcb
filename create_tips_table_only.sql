-- =====================================================
-- Создание таблицы советов (только структура)
-- =====================================================
-- Используйте этот файл для создания только таблицы без данных

-- Создание таблицы советов
CREATE TABLE IF NOT EXISTS tips (
    id SERIAL PRIMARY KEY,
    age_months INTEGER NOT NULL,
    content TEXT NOT NULL,
    category TEXT DEFAULT 'Общий',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Создание индексов для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_tips_age_months ON tips(age_months);
CREATE INDEX IF NOT EXISTS idx_tips_category ON tips(category);
CREATE INDEX IF NOT EXISTS idx_tips_age_category ON tips(age_months, category);

-- Включение Row Level Security (RLS)
ALTER TABLE tips ENABLE ROW LEVEL SECURITY;

-- Политика безопасности (разрешаем все операции для аутентифицированных пользователей)
CREATE POLICY "Enable all operations for authenticated users" ON tips FOR ALL USING (true);

-- Проверка создания таблицы
SELECT 'Таблица tips создана успешно!' as status;
