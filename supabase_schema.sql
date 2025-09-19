-- Схема базы данных для BabyBot в Supabase (PostgreSQL)
-- Этот скрипт создает все необходимые таблицы для работы бота

-- Таблица семей
CREATE TABLE IF NOT EXISTS families (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Таблица членов семьи
CREATE TABLE IF NOT EXISTS family_members (
    family_id INTEGER REFERENCES families(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    role TEXT DEFAULT 'Родитель',
    name TEXT DEFAULT 'Неизвестно',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (family_id, user_id)
);

-- Таблица кормлений
CREATE TABLE IF NOT EXISTS feedings (
    id SERIAL PRIMARY KEY,
    family_id INTEGER REFERENCES families(id) ON DELETE CASCADE,
    author_id BIGINT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    author_role TEXT DEFAULT 'Родитель',
    author_name TEXT DEFAULT 'Неизвестно',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Таблица смены подгузников
CREATE TABLE IF NOT EXISTS diapers (
    id SERIAL PRIMARY KEY,
    family_id INTEGER REFERENCES families(id) ON DELETE CASCADE,
    author_id BIGINT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    author_role TEXT DEFAULT 'Родитель',
    author_name TEXT DEFAULT 'Неизвестно',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Таблица купаний
CREATE TABLE IF NOT EXISTS baths (
    id SERIAL PRIMARY KEY,
    family_id INTEGER REFERENCES families(id) ON DELETE CASCADE,
    author_id BIGINT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    author_role TEXT DEFAULT 'Родитель',
    author_name TEXT DEFAULT 'Неизвестно',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Таблица активностей (игры, выкладывание на живот)
CREATE TABLE IF NOT EXISTS activities (
    id SERIAL PRIMARY KEY,
    family_id INTEGER REFERENCES families(id) ON DELETE CASCADE,
    author_id BIGINT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    activity_type TEXT DEFAULT 'Игра',
    author_role TEXT DEFAULT 'Родитель',
    author_name TEXT DEFAULT 'Неизвестно',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Таблица сессий сна
CREATE TABLE IF NOT EXISTS sleep_sessions (
    id SERIAL PRIMARY KEY,
    family_id INTEGER REFERENCES families(id) ON DELETE CASCADE,
    author_id BIGINT NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    duration_minutes INTEGER,
    author_role TEXT DEFAULT 'Родитель',
    author_name TEXT DEFAULT 'Неизвестно',
    feeding_notification_sent BOOLEAN DEFAULT FALSE,
    diaper_notification_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Таблица советов
CREATE TABLE IF NOT EXISTS tips (
    id SERIAL PRIMARY KEY,
    age_months INTEGER NOT NULL,
    content TEXT NOT NULL,
    category TEXT DEFAULT 'Общий',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Таблица настроек
CREATE TABLE IF NOT EXISTS settings (
    family_id INTEGER REFERENCES families(id) ON DELETE CASCADE PRIMARY KEY,
    feed_interval INTEGER DEFAULT 3,
    diaper_interval INTEGER DEFAULT 2,
    tips_enabled BOOLEAN DEFAULT TRUE,
    tips_time_hour INTEGER DEFAULT 9,
    tips_time_minute INTEGER DEFAULT 0,
    bath_reminder_enabled BOOLEAN DEFAULT TRUE,
    bath_reminder_hour INTEGER DEFAULT 19,
    bath_reminder_minute INTEGER DEFAULT 0,
    bath_reminder_period INTEGER DEFAULT 1,
    activity_reminder_enabled BOOLEAN DEFAULT TRUE,
    activity_reminder_interval INTEGER DEFAULT 2,
    sleep_monitoring_enabled BOOLEAN DEFAULT TRUE,
    baby_age_months INTEGER DEFAULT 0,
    baby_birth_date TEXT,
    birth_date TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Создание индексов для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_family_members_user_id ON family_members(user_id);
CREATE INDEX IF NOT EXISTS idx_feedings_family_id ON feedings(family_id);
CREATE INDEX IF NOT EXISTS idx_feedings_timestamp ON feedings(timestamp);
CREATE INDEX IF NOT EXISTS idx_diapers_family_id ON diapers(family_id);
CREATE INDEX IF NOT EXISTS idx_diapers_timestamp ON diapers(timestamp);
CREATE INDEX IF NOT EXISTS idx_baths_family_id ON baths(family_id);
CREATE INDEX IF NOT EXISTS idx_baths_timestamp ON baths(timestamp);
CREATE INDEX IF NOT EXISTS idx_activities_family_id ON activities(family_id);
CREATE INDEX IF NOT EXISTS idx_activities_timestamp ON activities(timestamp);
CREATE INDEX IF NOT EXISTS idx_sleep_sessions_family_id ON sleep_sessions(family_id);
CREATE INDEX IF NOT EXISTS idx_sleep_sessions_start_time ON sleep_sessions(start_time);
CREATE INDEX IF NOT EXISTS idx_tips_age_months ON tips(age_months);
CREATE INDEX IF NOT EXISTS idx_tips_category ON tips(category);

-- Функция для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггер для автоматического обновления updated_at в таблице settings
CREATE TRIGGER update_settings_updated_at 
    BEFORE UPDATE ON settings 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Включение Row Level Security (RLS) для безопасности
ALTER TABLE families ENABLE ROW LEVEL SECURITY;
ALTER TABLE family_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE feedings ENABLE ROW LEVEL SECURITY;
ALTER TABLE diapers ENABLE ROW LEVEL SECURITY;
ALTER TABLE baths ENABLE ROW LEVEL SECURITY;
ALTER TABLE activities ENABLE ROW LEVEL SECURITY;
ALTER TABLE sleep_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE tips ENABLE ROW LEVEL SECURITY;

-- Политики безопасности (разрешаем все операции для аутентифицированных пользователей)
-- В реальном проекте здесь должны быть более строгие политики
CREATE POLICY "Enable all operations for authenticated users" ON families FOR ALL USING (true);
CREATE POLICY "Enable all operations for authenticated users" ON family_members FOR ALL USING (true);
CREATE POLICY "Enable all operations for authenticated users" ON feedings FOR ALL USING (true);
CREATE POLICY "Enable all operations for authenticated users" ON diapers FOR ALL USING (true);
CREATE POLICY "Enable all operations for authenticated users" ON baths FOR ALL USING (true);
CREATE POLICY "Enable all operations for authenticated users" ON activities FOR ALL USING (true);
CREATE POLICY "Enable all operations for authenticated users" ON sleep_sessions FOR ALL USING (true);
CREATE POLICY "Enable all operations for authenticated users" ON settings FOR ALL USING (true);
CREATE POLICY "Enable all operations for authenticated users" ON tips FOR ALL USING (true);
