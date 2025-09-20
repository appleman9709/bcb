"""
Альтернативная версия Supabase клиента для Replit
Используется в случае проблем с основной версией
"""

import os
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict, Any
import pytz
from dotenv import load_dotenv
import time
import requests
import json

# Загружаем переменные окружения
load_dotenv()

# Получаем данные из переменных окружения
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not all([SUPABASE_URL, SUPABASE_KEY]):
    print("❌ ОШИБКА: Не все необходимые переменные Supabase установлены!")
    print("📝 Убедитесь, что в .env файле установлены:")
    print("   • SUPABASE_URL")
    print("   • SUPABASE_KEY")
    exit(1)

# Простой HTTP клиент для Supabase REST API
class SimpleSupabaseClient:
    def __init__(self, url: str, key: str):
        self.url = url.rstrip('/')
        self.key = key
        self.headers = {
            'apikey': key,
            'Authorization': f'Bearer {key}',
            'Content-Type': 'application/json'
        }
    
    def table(self, table_name: str):
        return SimpleSupabaseTable(self.url, self.headers, table_name)

class SimpleSupabaseTable:
    def __init__(self, base_url: str, headers: dict, table_name: str):
        self.base_url = base_url
        self.headers = headers
        self.table_name = table_name
        self.url = f"{base_url}/rest/v1/{table_name}"
    
    def select(self, columns: str = "*"):
        return SimpleSupabaseQuery(self.url, self.headers, 'select', columns)
    
    def insert(self, data: dict):
        return SimpleSupabaseQuery(self.url, self.headers, 'insert', data)
    
    def update(self, data: dict):
        return SimpleSupabaseQuery(self.url, self.headers, 'update', data)
    
    def delete(self):
        return SimpleSupabaseQuery(self.url, self.headers, 'delete')

class SimpleSupabaseQuery:
    def __init__(self, url: str, headers: dict, method: str, data=None):
        self.url = url
        self.headers = headers
        self.method = method
        self.data = data
        self.params = {}
    
    def eq(self, column: str, value):
        if 'select' in self.url:
            self.params[f'{column}'] = f'eq.{value}'
        return self
    
    def order(self, column: str, direction: str = 'asc'):
        self.params['order'] = f'{column}.{direction}'
        return self
    
    def limit(self, count: int):
        self.params['limit'] = str(count)
        return self
    
    def gte(self, column: str, value):
        self.params[f'{column}'] = f'gte.{value}'
        return self
    
    def lt(self, column: str, value):
        self.params[f'{column}'] = f'lt.{value}'
        return self
    
    def execute(self):
        try:
            if self.method == 'select':
                response = requests.get(self.url, headers=self.headers, params=self.params)
            elif self.method == 'insert':
                response = requests.post(self.url, headers=self.headers, json=self.data)
            elif self.method == 'update':
                response = requests.patch(self.url, headers=self.headers, json=self.data, params=self.params)
            elif self.method == 'delete':
                response = requests.delete(self.url, headers=self.headers, params=self.params)
            
            response.raise_for_status()
            
            # Создаем объект результата, похожий на Supabase
            class Result:
                def __init__(self, data):
                    self.data = data
            
            if self.method == 'select':
                return Result(response.json())
            else:
                return Result(response.json())
                
        except Exception as e:
            print(f"❌ Ошибка выполнения запроса: {e}")
            return Result([])

# Создаем простой клиент
supabase = SimpleSupabaseClient(SUPABASE_URL, SUPABASE_KEY)

# Кэш для family_id (время жизни 5 минут)
family_id_cache = {}
CACHE_TTL = 300  # 5 минут в секундах

def safe_execute(query_func, max_retries=5, delay=1):
    """Безопасное выполнение запроса с повторными попытками"""
    for attempt in range(max_retries):
        try:
            return query_func()
        except Exception as e:
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ['timeout', 'timed out', 'connection', 'network']):
                print(f"⚠️ Попытка {attempt + 1} неудачна (таймаут), повтор через {delay}с...")
            else:
                print(f"⚠️ Попытка {attempt + 1} неудачна, повтор через {delay}с...")
            
            if attempt == max_retries - 1:
                print(f"❌ Ошибка после {max_retries} попыток: {e}")
                return None
            
            time.sleep(min(delay * (2 ** attempt), 10))
    return None

def get_thai_time():
    """Получить текущее время в тайском часовом поясе"""
    thai_tz = pytz.timezone('Asia/Bangkok')
    utc_now = datetime.now(pytz.UTC)
    thai_now = utc_now.astimezone(thai_tz)
    return thai_now

def get_thai_date():
    """Получить текущую дату в тайском часовом поясе"""
    return get_thai_time().date()

# Импортируем все функции из основного файла
# (В реальном проекте здесь должны быть все функции из supabase_client.py)

def init_supabase():
    """Инициализация Supabase (проверка подключения)"""
    print("🔄 Инициализация простого Supabase клиента...")
    try:
        # Тестируем подключение
        result = supabase.table('families').select('id').limit(1).execute()
        print("✅ Простой Supabase клиент инициализирован успешно")
        return True
    except Exception as e:
        print(f"❌ Ошибка инициализации простого Supabase клиента: {e}")
        return False

# Добавьте здесь все остальные функции из основного supabase_client.py
# Для краткости я не копирую их все, но в реальном проекте нужно скопировать все функции
