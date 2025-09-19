#!/usr/bin/env python3
"""
Простой скрипт для добавления советов в Supabase
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Загружаем переменные окружения
load_dotenv()

# Инициализация Supabase
supabase: Client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

# Несколько тестовых советов
TEST_TIPS = [
    {
        'age_months': 0,
        'content': '🍼 Кормите малыша каждые 2-3 часа, даже ночью. Новорожденные едят часто и понемногу.',
        'category': 'Кормление'
    },
    {
        'age_months': 0,
        'content': '💤 Сон новорожденного составляет 16-18 часов в сутки. Не беспокойтесь, если малыш спит много.',
        'category': 'Сон'
    },
    {
        'age_months': 1,
        'content': '😊 Малыш начинает улыбаться! Это важный этап социального развития.',
        'category': 'Развитие'
    },
    {
        'age_months': 2,
        'content': '🤲 Малыш начинает хватать предметы. Давайте ему безопасные игрушки для развития моторики.',
        'category': 'Развитие'
    },
    {
        'age_months': 3,
        'content': '🔄 Малыш переворачивается с живота на спину. Убедитесь, что поверхность безопасна.',
        'category': 'Развитие'
    }
]

def add_test_tips():
    """Добавить тестовые советы"""
    print("🚀 Добавляем тестовые советы...")
    
    try:
        for tip in TEST_TIPS:
            result = supabase.table('tips').insert(tip).execute()
            print(f"✅ Добавлен совет для {tip['age_months']} месяцев: {tip['category']}")
        
        print(f"\n🎉 Успешно добавлено {len(TEST_TIPS)} тестовых советов!")
        
        # Проверяем результат
        result = supabase.table('tips').select('*').execute()
        print(f"📊 Всего советов в базе: {len(result.data)}")
        
    except Exception as e:
        print(f"❌ Ошибка при добавлении советов: {e}")
        print("💡 Убедитесь, что таблица 'tips' создана в Supabase")

if __name__ == "__main__":
    add_test_tips()
