#!/usr/bin/env python3
"""
Скрипт для создания таблицы советов в Supabase
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Загружаем переменные окружения
load_dotenv()

# Инициализация Supabase
supabase: Client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

def create_tips_table():
    """Создать таблицу советов"""
    print("🚀 Создаем таблицу советов...")
    
    try:
        # Создаем таблицу советов
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS tips (
            id SERIAL PRIMARY KEY,
            age_months INTEGER NOT NULL,
            content TEXT NOT NULL,
            category TEXT DEFAULT 'Общий',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        
        # Выполняем SQL запрос
        result = supabase.rpc('exec_sql', {'sql': create_table_sql}).execute()
        print("✅ Таблица советов создана!")
        
        # Создаем индексы
        index_sql = """
        CREATE INDEX IF NOT EXISTS idx_tips_age_months ON tips(age_months);
        CREATE INDEX IF NOT EXISTS idx_tips_category ON tips(category);
        """
        
        supabase.rpc('exec_sql', {'sql': index_sql}).execute()
        print("✅ Индексы созданы!")
        
        # Включаем RLS
        rls_sql = "ALTER TABLE tips ENABLE ROW LEVEL SECURITY;"
        supabase.rpc('exec_sql', {'sql': rls_sql}).execute()
        print("✅ RLS включен!")
        
        # Создаем политику безопасности
        policy_sql = "CREATE POLICY \"Enable all operations for authenticated users\" ON tips FOR ALL USING (true);"
        supabase.rpc('exec_sql', {'sql': policy_sql}).execute()
        print("✅ Политика безопасности создана!")
        
        print("\n🎉 Таблица советов успешно создана!")
        
    except Exception as e:
        print(f"❌ Ошибка при создании таблицы: {e}")
        print("💡 Возможно, нужно выполнить SQL запросы вручную в Supabase Dashboard")

if __name__ == "__main__":
    create_tips_table()
