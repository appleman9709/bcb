"""
Supabase клиент для BabyBot
Заменяет SQLite функции на Supabase PostgreSQL
"""

import os
from datetime import datetime, timedelta
from supabase import create_client, Client
from typing import Optional, List, Tuple, Dict, Any
import pytz
from dotenv import load_dotenv
import time

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

# Создаем клиент Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
            # Проверяем на специфические ошибки таймаута
            if any(keyword in error_msg for keyword in ['timeout', 'timed out', 'connection', 'network', 'read operation timed out']):
                print(f"⚠️ Попытка {attempt + 1} неудачна (таймаут), повтор через {delay}с...")
            else:
                print(f"⚠️ Попытка {attempt + 1} неудачна, повтор через {delay}с...")
            
            if attempt == max_retries - 1:
                print(f"❌ Ошибка после {max_retries} попыток: {e}")
                return None
            
            # Экспоненциальная задержка
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

# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ С СЕМЬЯМИ ====================

def get_family_id(user_id: int) -> Optional[int]:
    """Получить ID семьи пользователя с кэшированием"""
    current_time = time.time()
    
    # Проверяем кэш
    if user_id in family_id_cache:
        cached_data = family_id_cache[user_id]
        if current_time - cached_data['timestamp'] < CACHE_TTL:
            return cached_data['family_id']
        else:
            # Удаляем устаревший кэш
            del family_id_cache[user_id]
    
    def query():
        result = supabase.table('family_members').select('family_id').eq('user_id', user_id).execute()
        if result.data:
            return result.data[0]['family_id']
        return None
    
    result = safe_execute(query)
    if result is None:
        # Если произошла ошибка подключения, попробуем еще раз с увеличенной задержкой
        print(f"🔄 Повторная попытка получения family_id для пользователя {user_id}")
        time.sleep(2)
        result = safe_execute(query)
    
    # Кэшируем результат (даже если None)
    if result is not None:
        family_id_cache[user_id] = {
            'family_id': result,
            'timestamp': current_time
        }
    
    return result

def create_family(name: str, user_id: int) -> Optional[int]:
    """Создать новую семью"""
    def query():
        # Создаем семью
        family_result = supabase.table('families').insert({'name': name}).execute()
        family_id = family_result.data[0]['id']
        
        # Добавляем пользователя в семью
        supabase.table('family_members').insert({
            'family_id': family_id,
            'user_id': user_id,
            'role': 'Родитель',
            'name': 'Неизвестно'
        }).execute()
        
        # Создаем настройки по умолчанию
        supabase.table('settings').insert({
            'family_id': family_id,
            'feed_interval': 3,
            'diaper_interval': 2,
            'tips_enabled': True,
            'tips_time_hour': 9,
            'tips_time_minute': 0,
            'bath_reminder_enabled': True,
            'bath_reminder_hour': 19,
            'bath_reminder_minute': 0,
            'bath_reminder_period': 1,
            'activity_reminder_enabled': True,
            'activity_reminder_interval': 2,
            'baby_age_months': 0
        }).execute()
        
        return family_id
    
    result = safe_execute(query)
    
    # Очищаем кэш для этого пользователя при создании семьи
    if result and user_id in family_id_cache:
        del family_id_cache[user_id]
    
    return result

def join_family_by_code(code: str, user_id: int) -> Tuple[Optional[int], str]:
    """Присоединить пользователя к семье по коду приглашения"""
    def query():
        family_id = int(code)
        
        # Проверяем, существует ли семья
        family_result = supabase.table('families').select('id, name').eq('id', family_id).execute()
        if not family_result.data:
            return None, "Семья не найдена"
        
        family = family_result.data[0]
        
        # Проверяем, не состоит ли пользователь уже в семье
        existing_result = supabase.table('family_members').select('family_id').eq('user_id', user_id).execute()
        if existing_result.data:
            return None, "Вы уже состоите в семье"
        
        # Добавляем пользователя в семью
        supabase.table('family_members').insert({
            'family_id': family_id,
            'user_id': user_id,
            'role': 'Родитель',
            'name': 'Неизвестно'
        }).execute()
        
        return family_id, family['name']
    
    try:
        result = safe_execute(query)
        if result:
            family_id, family_name = result
            # Очищаем кэш для этого пользователя при присоединении к семье
            if user_id in family_id_cache:
                del family_id_cache[user_id]
            return family_id, family_name
        else:
            return None, "Ошибка присоединения к семье"
    except ValueError:
        return None, "Неверный код приглашения"
    except Exception as e:
        print(f"❌ Ошибка присоединения к семье: {e}")
        return None, "Ошибка присоединения к семье"

def get_family_name(family_id: int) -> str:
    """Получить название семьи по ID"""
    try:
        result = supabase.table('families').select('name').eq('id', family_id).execute()
        if result.data:
            return result.data[0]['name']
        return "Неизвестная семья"
    except Exception as e:
        print(f"❌ Ошибка получения названия семьи: {e}")
        return "Неизвестная семья"

def get_member_info(user_id: int) -> Tuple[Optional[str], Optional[str]]:
    """Получить информацию о члене семьи"""
    try:
        result = supabase.table('family_members').select('role, name').eq('user_id', user_id).execute()
        if result.data:
            member = result.data[0]
            return member['role'], member['name']
        return None, None
    except Exception as e:
        print(f"❌ Ошибка получения информации о члене семьи: {e}")
        return None, None

def set_member_role(user_id: int, role: str, name: str) -> bool:
    """Установить роль и имя для члена семьи"""
    try:
        supabase.table('family_members').update({
            'role': role,
            'name': name
        }).eq('user_id', user_id).execute()
        return True
    except Exception as e:
        print(f"❌ Ошибка установки роли: {e}")
        return False

def get_family_members_with_roles(family_id: int) -> List[Tuple[int, str, str]]:
    """Получить всех членов семьи с ролями"""
    try:
        result = supabase.table('family_members').select('user_id, role, name').eq('family_id', family_id).execute()
        return [(member['user_id'], member['role'], member['name']) for member in result.data]
    except Exception as e:
        print(f"❌ Ошибка получения членов семьи: {e}")
        return []

# ==================== ФУНКЦИИ ДЛЯ КОРМЛЕНИЙ ====================

def add_feeding(user_id: int, minutes_ago: int = 0, force: bool = False) -> bool:
    """Добавить запись о кормлении"""
    try:
        family_id = get_family_id(user_id)
        if not family_id:
            return False
        
        # Проверяем, не было ли кормления в последние 30 минут (если не принудительно)
        if not force and check_recent_feeding(family_id, 30):
            return False  # Возвращаем False для индикации дубликата
        
        role, name = get_member_info(user_id)
        if not role:
            role, name = 'Родитель', 'Неизвестно'
        
        timestamp = get_thai_time() - timedelta(minutes=minutes_ago)
        
        supabase.table('feedings').insert({
            'family_id': family_id,
            'author_id': user_id,
            'timestamp': timestamp.isoformat(),
            'author_role': role,
            'author_name': name
        }).execute()
        
        return True
    except Exception as e:
        print(f"❌ Ошибка добавления кормления: {e}")
        return False

def get_last_feeding_time(user_id: int) -> Optional[datetime]:
    """Получить время последнего кормления"""
    try:
        family_id = get_family_id(user_id)
        if not family_id:
            return None
        
        result = supabase.table('feedings').select('timestamp').eq('family_id', family_id).order('timestamp', desc=True).limit(1).execute()
        
        if result.data:
            timestamp_str = result.data[0]['timestamp']
            # Конвертируем UTC время в тайское время
            utc_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            thai_tz = pytz.timezone('Asia/Bangkok')
            return utc_time.astimezone(thai_tz)
        return None
    except Exception as e:
        print(f"❌ Ошибка получения времени последнего кормления: {e}")
        return None

def get_last_feeding_time_for_family(family_id: int) -> Optional[datetime]:
    """Получить время последнего кормления для семьи"""
    try:
        result = supabase.table('feedings').select('timestamp').eq('family_id', family_id).order('timestamp', desc=True).limit(1).execute()
        
        if result.data:
            timestamp_str = result.data[0]['timestamp']
            # Конвертируем UTC время в тайское время
            utc_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            thai_tz = pytz.timezone('Asia/Bangkok')
            return utc_time.astimezone(thai_tz)
        return None
    except Exception as e:
        print(f"❌ Ошибка получения времени последнего кормления для семьи: {e}")
        return None

# ==================== ФУНКЦИИ ДЛЯ ПОДГУЗНИКОВ ====================

def add_diaper_change(user_id: int, minutes_ago: int = 0, force: bool = False) -> bool:
    """Добавить запись о смене подгузника"""
    try:
        family_id = get_family_id(user_id)
        if not family_id:
            return False
        
        # Проверяем, не было ли смены подгузника в последние 30 минут (если не принудительно)
        if not force and check_recent_diaper_change(family_id, 30):
            return False  # Возвращаем False для индикации дубликата
        
        role, name = get_member_info(user_id)
        if not role:
            role, name = 'Родитель', 'Неизвестно'
        
        timestamp = get_thai_time() - timedelta(minutes=minutes_ago)
        
        supabase.table('diapers').insert({
            'family_id': family_id,
            'author_id': user_id,
            'timestamp': timestamp.isoformat(),
            'author_role': role,
            'author_name': name
        }).execute()
        
        return True
    except Exception as e:
        print(f"❌ Ошибка добавления смены подгузника: {e}")
        return False

def get_last_diaper_change_time_for_family(family_id: int) -> Optional[datetime]:
    """Получить время последней смены подгузника для семьи"""
    try:
        result = supabase.table('diapers').select('timestamp').eq('family_id', family_id).order('timestamp', desc=True).limit(1).execute()
        
        if result.data:
            timestamp_str = result.data[0]['timestamp']
            # Конвертируем UTC время в тайское время
            utc_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            thai_tz = pytz.timezone('Asia/Bangkok')
            return utc_time.astimezone(thai_tz)
        return None
    except Exception as e:
        print(f"❌ Ошибка получения времени последней смены подгузника: {e}")
        return None

def get_last_diaper_change_for_family(family_id: int) -> Optional[datetime]:
    """Получить время последней смены подгузника для семьи (алиас)"""
    return get_last_diaper_change_time_for_family(family_id)

def check_recent_feeding(family_id: int, minutes_threshold: int = 30) -> bool:
    """Проверить, было ли кормление в последние N минут"""
    try:
        last_feeding = get_last_feeding_time_for_family(family_id)
        if not last_feeding:
            return False
        
        now = get_thai_time()
        time_diff = now - last_feeding
        minutes_ago = int(time_diff.total_seconds() / 60)
        
        return minutes_ago < minutes_threshold
    except Exception as e:
        print(f"❌ Ошибка проверки последнего кормления: {e}")
        return False

def check_recent_diaper_change(family_id: int, minutes_threshold: int = 30) -> bool:
    """Проверить, была ли смена подгузника в последние N минут"""
    try:
        last_diaper = get_last_diaper_change_time_for_family(family_id)
        if not last_diaper:
            return False
        
        now = get_thai_time()
        time_diff = now - last_diaper
        minutes_ago = int(time_diff.total_seconds() / 60)
        
        return minutes_ago < minutes_threshold
    except Exception as e:
        print(f"❌ Ошибка проверки последней смены подгузника: {e}")
        return False

# ==================== ФУНКЦИИ ДЛЯ НАСТРОЕК ====================

def get_user_intervals(family_id: int) -> Tuple[int, int]:
    """Получить интервалы кормления и смены подгузников"""
    try:
        result = supabase.table('settings').select('feed_interval, diaper_interval').eq('family_id', family_id).execute()
        if result.data:
            settings = result.data[0]
            return settings['feed_interval'], settings['diaper_interval']
        return 3, 2
    except Exception as e:
        print(f"❌ Ошибка получения интервалов: {e}")
        return 3, 2

def set_user_interval(family_id: int, feed_interval: Optional[int] = None, diaper_interval: Optional[int] = None) -> bool:
    """Установить интервалы кормления и смены подгузников"""
    try:
        update_data = {}
        if feed_interval is not None:
            update_data['feed_interval'] = feed_interval
        if diaper_interval is not None:
            update_data['diaper_interval'] = diaper_interval
        
        if update_data:
            supabase.table('settings').update(update_data).eq('family_id', family_id).execute()
        return True
    except Exception as e:
        print(f"❌ Ошибка установки интервалов: {e}")
        return False

def get_birth_date(family_id: int) -> Optional[str]:
    """Получить дату рождения малыша"""
    try:
        result = supabase.table('settings').select('baby_birth_date').eq('family_id', family_id).execute()
        if result.data and result.data[0]['baby_birth_date']:
            return result.data[0]['baby_birth_date']
        return None
    except Exception as e:
        print(f"❌ Ошибка получения даты рождения: {e}")
        return None

def set_birth_date(family_id: int, birth_date: str) -> bool:
    """Установить дату рождения малыша"""
    try:
        supabase.table('settings').update({'baby_birth_date': birth_date}).eq('family_id', family_id).execute()
        
        # Автоматически вычисляем и обновляем возраст
        age_months = get_baby_age_months(family_id)
        if age_months > 0:
            set_baby_age_months(family_id, age_months)
            print(f"✅ Возраст малыша обновлен: {age_months} месяцев")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка установки даты рождения: {e}")
        return False

def get_baby_age_months(family_id: int) -> int:
    """Получить возраст малыша в месяцах на основе даты рождения"""
    try:
        from datetime import datetime
        
        # Получаем дату рождения
        birth_date_str = get_birth_date(family_id)
        if not birth_date_str:
            return 0
        
        # Парсим дату рождения
        birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d')
        
        # Получаем текущую дату
        now = get_thai_time()
        
        # Вычисляем возраст в месяцах
        age_months = (now.year - birth_date.year) * 12 + (now.month - birth_date.month)
        
        # Если день рождения еще не наступил в этом месяце, уменьшаем на 1
        if now.day < birth_date.day:
            age_months -= 1
        
        # Возраст не может быть отрицательным
        return max(0, age_months)
        
    except Exception as e:
        print(f"❌ Ошибка получения возраста малыша: {e}")
        return 0

def set_baby_age_months(family_id: int, age_months: int) -> bool:
    """Установить возраст малыша в месяцах"""
    try:
        supabase.table('settings').update({'baby_age_months': age_months}).eq('family_id', family_id).execute()
        return True
    except Exception as e:
        print(f"❌ Ошибка установки возраста малыша: {e}")
        return False

# ==================== ФУНКЦИИ ДЛЯ КУПАНИЙ ====================

def add_bath(user_id: int, minutes_ago: int = 0) -> bool:
    """Добавить запись о купании"""
    try:
        family_id = get_family_id(user_id)
        if not family_id:
            return False
        
        role, name = get_member_info(user_id)
        if not role:
            role, name = 'Родитель', 'Неизвестно'
        
        timestamp = get_thai_time() - timedelta(minutes=minutes_ago)
        
        supabase.table('baths').insert({
            'family_id': family_id,
            'author_id': user_id,
            'timestamp': timestamp.isoformat(),
            'author_role': role,
            'author_name': name
        }).execute()
        
        return True
    except Exception as e:
        print(f"❌ Ошибка добавления купания: {e}")
        return False

def get_last_bath_time_for_family(family_id: int) -> Optional[datetime]:
    """Получить время последнего купания для семьи"""
    try:
        result = supabase.table('baths').select('timestamp').eq('family_id', family_id).order('timestamp', desc=True).limit(1).execute()
        
        if result.data:
            timestamp_str = result.data[0]['timestamp']
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return None
    except Exception as e:
        print(f"❌ Ошибка получения времени последнего купания: {e}")
        return None

# ==================== ФУНКЦИИ ДЛЯ АКТИВНОСТЕЙ ====================

def add_activity(user_id: int, activity_type: str = 'Игра', minutes_ago: int = 0) -> bool:
    """Добавить запись об активности"""
    try:
        family_id = get_family_id(user_id)
        if not family_id:
            return False
        
        role, name = get_member_info(user_id)
        if not role:
            role, name = 'Родитель', 'Неизвестно'
        
        timestamp = get_thai_time() - timedelta(minutes=minutes_ago)
        
        supabase.table('activities').insert({
            'family_id': family_id,
            'author_id': user_id,
            'timestamp': timestamp.isoformat(),
            'activity_type': activity_type,
            'author_role': role,
            'author_name': name
        }).execute()
        
        return True
    except Exception as e:
        print(f"❌ Ошибка добавления активности: {e}")
        return False

def get_last_activity_time_for_family(family_id: int) -> Optional[datetime]:
    """Получить время последней активности для семьи"""
    try:
        result = supabase.table('activities').select('timestamp').eq('family_id', family_id).order('timestamp', desc=True).limit(1).execute()
        
        if result.data:
            timestamp_str = result.data[0]['timestamp']
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return None
    except Exception as e:
        print(f"❌ Ошибка получения времени последней активности: {e}")
        return None


# ==================== ФУНКЦИИ ДЛЯ СТАТИСТИКИ ====================

def get_feeding_stats(family_id: int, days: int = 7) -> Dict[str, Any]:
    """Получить статистику кормлений"""
    try:
        start_date = get_thai_time() - timedelta(days=days)
        
        result = supabase.table('feedings').select('timestamp').eq('family_id', family_id).gte('timestamp', start_date.isoformat()).execute()
        
        return {
            'count': len(result.data),
            'last_time': get_last_feeding_time_for_family(family_id)
        }
    except Exception as e:
        print(f"❌ Ошибка получения статистики кормлений: {e}")
        return {'count': 0, 'last_time': None}

def get_diaper_stats(family_id: int, days: int = 7) -> Dict[str, Any]:
    """Получить статистику смен подгузников"""
    try:
        start_date = get_thai_time() - timedelta(days=days)
        
        result = supabase.table('diapers').select('timestamp').eq('family_id', family_id).gte('timestamp', start_date.isoformat()).execute()
        
        return {
            'count': len(result.data),
            'last_time': get_last_diaper_change_time_for_family(family_id)
        }
    except Exception as e:
        print(f"❌ Ошибка получения статистики подгузников: {e}")
        return {'count': 0, 'last_time': None}

def get_bath_stats(family_id: int, days: int = 7) -> Dict[str, Any]:
    """Получить статистику купаний"""
    try:
        start_date = get_thai_time() - timedelta(days=days)
        
        result = supabase.table('baths').select('timestamp').eq('family_id', family_id).gte('timestamp', start_date.isoformat()).execute()
        
        return {
            'count': len(result.data),
            'last_time': get_last_bath_time_for_family(family_id)
        }
    except Exception as e:
        print(f"❌ Ошибка получения статистики купаний: {e}")
        return {'count': 0, 'last_time': None}

def get_activity_stats(family_id: int, days: int = 7) -> Dict[str, Any]:
    """Получить статистику активностей"""
    try:
        start_date = get_thai_time() - timedelta(days=days)
        
        result = supabase.table('activities').select('timestamp').eq('family_id', family_id).gte('timestamp', start_date.isoformat()).execute()
        
        return {
            'count': len(result.data),
            'last_time': get_last_activity_time_for_family(family_id)
        }
    except Exception as e:
        print(f"❌ Ошибка получения статистики активностей: {e}")
        return {'count': 0, 'last_time': None}

# ==================== ФУНКЦИИ ДЛЯ НАСТРОЕК УВЕДОМЛЕНИЙ ====================

def get_notification_settings(family_id: int) -> Dict[str, Any]:
    """Получить настройки уведомлений"""
    try:
        result = supabase.table('settings').select('*').eq('family_id', family_id).execute()
        if result.data:
            return result.data[0]
        return {}
    except Exception as e:
        print(f"❌ Ошибка получения настроек уведомлений: {e}")
        return {}

def update_notification_settings(family_id: int, settings: Dict[str, Any]) -> bool:
    """Обновить настройки уведомлений"""
    try:
        supabase.table('settings').update(settings).eq('family_id', family_id).execute()
        return True
    except Exception as e:
        print(f"❌ Ошибка обновления настроек уведомлений: {e}")
        return False

# ==================== ФУНКЦИИ ДЛЯ СОВЕТОВ ====================

def get_random_tip(age_months: int) -> Optional[str]:
    """Получить случайный совет для возраста из базы данных"""
    try:
        import random
        
        # Получаем советы из базы данных для точного возраста
        result = supabase.table('tips').select('content').eq('age_months', age_months).execute()
        
        if result.data:
            return random.choice(result.data)['content']
        
        # Если нет советов для точного возраста, ищем ближайший доступный возраст
        # Сначала ищем для меньших возрастов (более подходящие советы)
        for check_age in range(age_months - 1, -1, -1):
            result = supabase.table('tips').select('content').eq('age_months', check_age).execute()
            if result.data:
                return random.choice(result.data)['content']
        
        # Если не нашли для меньших возрастов, ищем для больших возрастов
        for check_age in range(age_months + 1, 13):  # до 12 месяцев
            result = supabase.table('tips').select('content').eq('age_months', check_age).execute()
            if result.data:
                return random.choice(result.data)['content']
        
        # Если вообще нет советов в базе данных, возвращаем общий совет
        return "💡 Помните: каждый малыш уникален! Следуйте рекомендациям педиатра и доверяйте своей интуиции."
        
    except Exception as e:
        print(f"❌ Ошибка получения совета: {e}")
        return "💡 Помните: каждый малыш уникален! Следуйте рекомендациям педиатра и доверяйте своей интуиции."

def get_tips_by_category(age_months: int, category: str) -> List[str]:
    """Получить советы по категории для возраста"""
    try:
        result = supabase.table('tips').select('content').eq('age_months', age_months).eq('category', category).execute()
        return [tip['content'] for tip in result.data]
    except Exception as e:
        print(f"❌ Ошибка получения советов по категории: {e}")
        return []

def get_all_categories() -> List[str]:
    """Получить все доступные категории советов"""
    try:
        result = supabase.table('tips').select('category').execute()
        categories = list(set([tip['category'] for tip in result.data]))
        return sorted(categories)
    except Exception as e:
        print(f"❌ Ошибка получения категорий: {e}")
        return []

# ==================== ФУНКЦИИ ДЛЯ ИСТОРИИ ====================

def get_feeding_history(family_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Получить историю кормлений"""
    try:
        result = supabase.table('feedings').select('*').eq('family_id', family_id).order('timestamp', desc=True).limit(limit).execute()
        return result.data
    except Exception as e:
        print(f"❌ Ошибка получения истории кормлений: {e}")
        return []

def get_diaper_history(family_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Получить историю смен подгузников"""
    try:
        result = supabase.table('diapers').select('*').eq('family_id', family_id).order('timestamp', desc=True).limit(limit).execute()
        return result.data
    except Exception as e:
        print(f"❌ Ошибка получения истории подгузников: {e}")
        return []

def get_bath_history(family_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Получить историю купаний"""
    try:
        result = supabase.table('baths').select('*').eq('family_id', family_id).order('timestamp', desc=True).limit(limit).execute()
        return result.data
    except Exception as e:
        print(f"❌ Ошибка получения истории купаний: {e}")
        return []

def get_activity_history(family_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Получить историю активностей"""
    try:
        result = supabase.table('activities').select('*').eq('family_id', family_id).order('timestamp', desc=True).limit(limit).execute()
        return result.data
    except Exception as e:
        print(f"❌ Ошибка получения истории активностей: {e}")
        return []


# ==================== ФУНКЦИИ ДЛЯ ПРОВЕРКИ ПОДКЛЮЧЕНИЯ ====================

def test_connection() -> bool:
    """Проверить подключение к Supabase"""
    def query():
        result = supabase.table('families').select('id').limit(1).execute()
        return True
    
    try:
        result = safe_execute(query, max_retries=2, delay=2)
        if result:
            print("✅ Подключение к Supabase успешно")
            return True
        else:
            print("❌ Не удалось подключиться к Supabase после повторных попыток")
            return False
    except Exception as e:
        print(f"❌ Критическая ошибка подключения к Supabase: {e}")
        return False

# ==================== ФУНКЦИИ ДЛЯ НАПОМИНАНИЙ ====================

def get_families_needing_feeding_reminder() -> List[Dict[str, Any]]:
    """Получить семьи, которым нужно напоминание о кормлении"""
    try:
        # Получаем все семьи с их настройками
        families_result = supabase.table('settings').select('family_id, feed_interval').execute()
        
        families_needing_reminder = []
        
        for family in families_result.data:
            family_id = family['family_id']
            feed_interval = family['feed_interval']
            
            # Получаем время последнего кормления
            last_feeding = get_last_feeding_time_for_family(family_id)
            if not last_feeding:
                # Если кормлений не было, проверяем, прошло ли больше 1 часа
                continue
            
            # Вычисляем время с последнего кормления
            now = get_thai_time()
            time_diff = now - last_feeding
            hours_since_feeding = time_diff.total_seconds() / 3600
            
            # Если прошло больше интервала кормления
            if hours_since_feeding >= feed_interval:
                families_needing_reminder.append({
                    'family_id': family_id,
                    'hours_since_feeding': hours_since_feeding,
                    'feed_interval': feed_interval
                })
        
        return families_needing_reminder
    except Exception as e:
        print(f"❌ Ошибка получения семей для напоминания о кормлении: {e}")
        return []

def get_families_needing_diaper_reminder() -> List[Dict[str, Any]]:
    """Получить семьи, которым нужно напоминание о смене подгузника"""
    try:
        # Получаем все семьи с их настройками
        families_result = supabase.table('settings').select('family_id, diaper_interval').execute()
        
        families_needing_reminder = []
        
        for family in families_result.data:
            family_id = family['family_id']
            diaper_interval = family['diaper_interval']
            
            # Получаем время последней смены подгузника
            last_diaper = get_last_diaper_change_time_for_family(family_id)
            if not last_diaper:
                # Если смен подгузника не было, проверяем, прошло ли больше 1 часа
                continue
            
            # Вычисляем время с последней смены
            now = get_thai_time()
            time_diff = now - last_diaper
            hours_since_diaper = time_diff.total_seconds() / 3600
            
            # Если прошло больше интервала смены подгузника
            if hours_since_diaper >= diaper_interval:
                families_needing_reminder.append({
                    'family_id': family_id,
                    'hours_since_diaper': hours_since_diaper,
                    'diaper_interval': diaper_interval
                })
        
        return families_needing_reminder
    except Exception as e:
        print(f"❌ Ошибка получения семей для напоминания о смене подгузника: {e}")
        return []

def get_family_members_for_notification(family_id: int) -> List[int]:
    """Получить список user_id всех членов семьи для отправки уведомлений"""
    try:
        result = supabase.table('family_members').select('user_id').eq('family_id', family_id).execute()
        return [member['user_id'] for member in result.data]
    except Exception as e:
        print(f"❌ Ошибка получения членов семьи для уведомлений: {e}")
        return []

def check_smart_reminder_conditions(family_id: int) -> Dict[str, Any]:
    """Проверить условия для напоминаний"""
    try:
        # Получаем настройки семьи
        settings = get_notification_settings(family_id)
        if not settings:
            return {'needs_feeding': False, 'needs_diaper': False}
        
        feed_interval = settings.get('feed_interval', 3)
        diaper_interval = settings.get('diaper_interval', 2)
        
        # Проверяем кормление
        last_feeding = get_last_feeding_time_for_family(family_id)
        needs_feeding = False
        hours_since_feeding = 0
        
        if last_feeding:
            now = get_thai_time()
            time_diff = now - last_feeding
            hours_since_feeding = time_diff.total_seconds() / 3600
            needs_feeding = hours_since_feeding >= feed_interval
        else:
            # Если кормлений не было, напоминаем через 1 час
            needs_feeding = True
            hours_since_feeding = 24  # Большое значение для отображения
        
        # Проверяем смену подгузника
        last_diaper = get_last_diaper_change_time_for_family(family_id)
        needs_diaper = False
        hours_since_diaper = 0
        
        if last_diaper:
            now = get_thai_time()
            time_diff = now - last_diaper
            hours_since_diaper = time_diff.total_seconds() / 3600
            needs_diaper = hours_since_diaper >= diaper_interval
        else:
            # Если смен подгузника не было, напоминаем через 1 час
            needs_diaper = True
            hours_since_diaper = 24  # Большое значение для отображения
        
        return {
            'needs_feeding': needs_feeding,
            'needs_diaper': needs_diaper,
            'hours_since_feeding': hours_since_feeding,
            'hours_since_diaper': hours_since_diaper,
            'feed_interval': feed_interval,
            'diaper_interval': diaper_interval
        }
    except Exception as e:
        print(f"❌ Ошибка проверки условий напоминаний: {e}")
        return {'needs_feeding': False, 'needs_diaper': False}

def get_smart_reminder_message(family_id: int) -> Optional[str]:
    """Получить сообщение напоминания для семьи"""
    try:
        conditions = check_smart_reminder_conditions(family_id)
        
        if not conditions['needs_feeding'] and not conditions['needs_diaper']:
            return None
        
        # Определяем основной заголовок в зависимости от того, что нужно
        if conditions['needs_feeding'] and conditions['needs_diaper']:
            message = "🔔 **Время кормления и смены подгузника!**\n\n"
        elif conditions['needs_feeding']:
            message = "🍼 **Время кормления!**\n\n"
        else:
            message = "💩 **Время смены подгузника!**\n\n"
        
        if conditions['needs_feeding']:
            hours = int(conditions['hours_since_feeding'])
            minutes = int((conditions['hours_since_feeding'] - hours) * 60)
            
            if hours > 0:
                time_str = f"{hours}ч {minutes}м"
            else:
                time_str = f"{minutes}м"
            
            if conditions['hours_since_feeding'] >= 24:
                message += f"🍼 **Кормление:**\n"
                message += f"• Последний раз кормили: давно\n"
                message += f"• Интервал: {conditions['feed_interval']}ч\n\n"
            else:
                message += f"🍼 **Кормление:**\n"
                message += f"• Прошло: {time_str}\n"
                message += f"• Интервал: {conditions['feed_interval']}ч\n\n"
        
        if conditions['needs_diaper']:
            hours = int(conditions['hours_since_diaper'])
            minutes = int((conditions['hours_since_diaper'] - hours) * 60)
            
            if hours > 0:
                time_str = f"{hours}ч {minutes}м"
            else:
                time_str = f"{minutes}м"
            
            if conditions['hours_since_diaper'] >= 24:
                message += f"💩 **Смена подгузника:**\n"
                message += f"• Последняя смена: давно\n"
                message += f"• Интервал: {conditions['diaper_interval']}ч\n\n"
            else:
                message += f"💩 **Смена подгузника:**\n"
                message += f"• Прошло: {time_str}\n"
                message += f"• Интервал: {conditions['diaper_interval']}ч\n\n"
        
        message += "💡 **Быстрые действия:**"
        
        return message
    except Exception as e:
        print(f"❌ Ошибка создания сообщения напоминания: {e}")
        return None

def get_all_families() -> List[int]:
    """Получить список всех ID семей"""
    try:
        result = supabase.table('families').select('id').execute()
        return [family['id'] for family in result.data]
    except Exception as e:
        print(f"❌ Ошибка получения списка семей: {e}")
        return []

# ==================== ФУНКЦИИ ДЛЯ УПРАВЛЕНИЯ КЭШЕМ ====================

def clear_family_cache(user_id: int = None):
    """Очистить кэш family_id"""
    if user_id:
        if user_id in family_id_cache:
            del family_id_cache[user_id]
            print(f"🧹 Кэш family_id очищен для пользователя {user_id}")
    else:
        family_id_cache.clear()
        print("🧹 Весь кэш family_id очищен")

def get_cache_stats():
    """Получить статистику кэша"""
    current_time = time.time()
    active_entries = 0
    expired_entries = 0
    
    for user_id, data in family_id_cache.items():
        if current_time - data['timestamp'] < CACHE_TTL:
            active_entries += 1
        else:
            expired_entries += 1
    
    return {
        'total_entries': len(family_id_cache),
        'active_entries': active_entries,
        'expired_entries': expired_entries
    }

# ==================== ИНИЦИАЛИЗАЦИЯ ====================

def init_supabase():
    """Инициализация Supabase (проверка подключения)"""
    print("🔄 Инициализация Supabase...")
    if test_connection():
        print("✅ Supabase инициализирован успешно")
        return True
    else:
        print("❌ Ошибка инициализации Supabase")
        return False
