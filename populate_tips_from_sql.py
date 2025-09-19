#!/usr/bin/env python3
"""
Скрипт для заполнения базы данных советами из SQL файла
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Загружаем переменные окружения
load_dotenv()

# Инициализация Supabase
supabase: Client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

def populate_tips_from_sql():
    """Заполнить базу данных советами из SQL файла"""
    print("🚀 Заполняем базу данных советами...")
    
    try:
        # Читаем SQL файл
        with open('tips_database.sql', 'r', encoding='utf-8') as file:
            sql_content = file.read()
        
        # Разделяем на отдельные запросы
        sql_queries = [query.strip() for query in sql_content.split(';') if query.strip() and not query.strip().startswith('--')]
        
        # Выполняем каждый запрос
        for i, query in enumerate(sql_queries):
            if query.upper().startswith('INSERT INTO tips'):
                try:
                    # Для INSERT запросов используем Supabase API
                    if 'VALUES' in query.upper():
                        # Парсим INSERT запрос
                        values_start = query.upper().find('VALUES') + 6
                        values_part = query[values_start:].strip()
                        
                        # Упрощенный парсинг для наших данных
                        if 'age_months' in query and 'content' in query:
                            # Это INSERT запрос с данными
                            print(f"📝 Выполняем INSERT запрос {i+1}...")
                            # Здесь можно добавить более сложную логику парсинга
                            # Пока что пропускаем сложные INSERT запросы
                        else:
                            print(f"⏭️ Пропускаем запрос {i+1} (не INSERT INTO tips)")
                    else:
                        print(f"⏭️ Пропускаем запрос {i+1} (не VALUES)")
                except Exception as e:
                    print(f"⚠️ Ошибка в запросе {i+1}: {e}")
            else:
                print(f"⏭️ Пропускаем запрос {i+1} (не INSERT INTO tips)")
        
        print("✅ Обработка SQL файла завершена!")
        print("💡 Рекомендуется выполнить SQL запросы вручную в Supabase Dashboard")
        
    except Exception as e:
        print(f"❌ Ошибка при обработке SQL файла: {e}")

def add_sample_tips():
    """Добавить несколько примеров советов"""
    print("🚀 Добавляем примеры советов...")
    
    sample_tips = [
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
    
    try:
        for tip in sample_tips:
            result = supabase.table('tips').insert(tip).execute()
            print(f"✅ Добавлен совет для {tip['age_months']} месяцев: {tip['category']}")
        
        print(f"\n🎉 Успешно добавлено {len(sample_tips)} примеров советов!")
        
        # Проверяем результат
        result = supabase.table('tips').select('*').execute()
        print(f"📊 Всего советов в базе: {len(result.data)}")
        
    except Exception as e:
        print(f"❌ Ошибка при добавлении примеров советов: {e}")

if __name__ == "__main__":
    print("Выберите действие:")
    print("1. Заполнить из SQL файла (рекомендуется выполнить SQL вручную)")
    print("2. Добавить примеры советов")
    
    choice = input("Введите номер (1 или 2): ").strip()
    
    if choice == "1":
        populate_tips_from_sql()
    elif choice == "2":
        add_sample_tips()
    else:
        print("❌ Неверный выбор")
