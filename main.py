from telethon import TelegramClient, events, Button
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import threading
import time
import http.server
import socketserver
import pytz
import subprocess
from typing import Optional

import os
from dotenv import load_dotenv

try:
    from supabase_client import (
        init_supabase, get_family_id, create_family, join_family_by_code, get_family_name, 
        get_member_info, set_member_role, get_family_members_with_roles,
        add_feeding, get_last_feeding_time, get_last_feeding_time_for_family,
        add_diaper_change, get_last_diaper_change_time_for_family, get_last_diaper_change_for_family,
        check_recent_feeding, check_recent_diaper_change,
        get_user_intervals, set_user_interval, get_birth_date, set_birth_date,
        get_baby_age_months, set_baby_age_months,
        add_bath, get_last_bath_time_for_family,
        add_activity, get_last_activity_time_for_family,
        get_feeding_stats, get_diaper_stats, get_bath_stats, get_activity_stats,
        get_notification_settings, update_notification_settings,
        get_random_tip, get_feeding_history, get_diaper_history, get_bath_history,
        get_activity_history, test_connection,
        # Функции для напоминаний
        check_smart_reminder_conditions, get_smart_reminder_message, 
        get_family_members_for_notification, get_all_families, get_thai_time,
        # Новые функции для системы уведомлений
        check_pre_reminder_conditions, check_overdue_reminder_conditions,
        get_pre_reminder_message, get_overdue_reminder_message,
        get_time_until_next_feeding, get_time_until_next_diaper_change,
        # Функции для отслеживания уведомлений
        log_notification_sent, check_recent_notification, acknowledge_notification,
        cleanup_old_notifications
    )
    print("✅ Основной Supabase клиент загружен успешно")
except Exception as e:
    print(f"❌ Ошибка загрузки основного Supabase клиента: {e}")
    print("🔄 Попытка загрузить альтернативную версию...")
    try:
        from supabase_client_fallback import (
            init_supabase, get_family_id, create_family, join_family_by_code, get_family_name, 
            get_member_info, set_member_role, get_family_members_with_roles,
            add_feeding, get_last_feeding_time, get_last_feeding_time_for_family,
            add_diaper_change, get_last_diaper_change_time_for_family, get_last_diaper_change_for_family,
            check_recent_feeding, check_recent_diaper_change,
            get_user_intervals, set_user_interval, get_birth_date, set_birth_date,
            get_baby_age_months, set_baby_age_months,
            add_bath, get_last_bath_time_for_family,
            add_activity, get_last_activity_time_for_family,
            get_feeding_stats, get_diaper_stats, get_bath_stats, get_activity_stats,
            get_notification_settings, update_notification_settings,
            get_random_tip, get_feeding_history, get_diaper_history, get_bath_history,
            get_activity_history, test_connection,
            # Функции для напоминаний
            check_smart_reminder_conditions, get_smart_reminder_message, 
            get_family_members_for_notification, get_all_families, get_thai_time,
            # Новые функции для системы уведомлений
            check_pre_reminder_conditions, check_overdue_reminder_conditions,
            get_pre_reminder_message, get_overdue_reminder_message,
            get_time_until_next_feeding, get_time_until_next_diaper_change,
            # Функции для отслеживания уведомлений
            log_notification_sent, check_recent_notification, acknowledge_notification,
            cleanup_old_notifications
        )
        print("✅ Альтернативный Supabase клиент загружен успешно")
    except Exception as e2:
        print(f"❌ Критическая ошибка загрузки Supabase клиента: {e2}")
        print("🛑 Бот не может работать без Supabase")
        exit(1)

load_dotenv()

API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
REPLIT_EXTERNAL_URL = os.getenv('REPLIT_EXTERNAL_URL')  # Для UptimeRobot

if not all([API_ID, API_HASH, BOT_TOKEN]):
    print("❌ ОШИБКА: Не все необходимые переменные окружения установлены!")
    print("📝 Убедитесь, что в .env файле или переменных окружения установлены:")
    print("   • API_ID")
    print("   • API_HASH") 
    print("   • BOT_TOKEN")
    print("🔧 Создайте .env файл на основе env.example")
    exit(1)

try:
    API_ID = int(API_ID)
except ValueError:
    print("❌ ОШИБКА: API_ID должен быть числом!")
    exit(1)

print("✅ Все переменные окружения загружены успешно")


def parse_time_input(time_str: str) -> Optional[int]:
    """Парсит строку времени и возвращает количество минут назад"""
    try:
        time_str = time_str.strip().lower()
        
        # Если только число - считаем минутами
        if time_str.isdigit():
            return int(time_str)
        
        # Если содержит "ч" - часы
        if "ч" in time_str:
            hours = int(time_str.replace("ч", "").strip())
            return hours * 60
        
        # Если содержит ":" - часы:минуты
        if ":" in time_str:
            parts = time_str.split(":")
            hours = int(parts[0])
            minutes = int(parts[1])
            return hours * 60 + minutes
        
        return None
    except:
        return None

def parse_time_setting(time_str: str) -> Optional[tuple]:
    """Парсит строку времени для настроек и возвращает (часы, минуты)"""
    try:
        time_str = time_str.strip()
        
        # Если только число - считаем часами
        if time_str.isdigit():
            hours = int(time_str)
            return (hours, 0)
        
        # Если содержит ":" - часы:минуты
        if ":" in time_str:
            parts = time_str.split(":")
            hours = int(parts[0])
            minutes = int(parts[1])
            return (hours, minutes)
        
        return None
    except:
        return None

def parse_birth_date(date_str: str) -> Optional[str]:
    """Парсит строку даты рождения и возвращает дату в формате YYYY-MM-DD"""
    try:
        date_str = date_str.strip()
        
        # Формат YYYY-MM-DD
        if len(date_str) == 10 and date_str.count('-') == 2:
            parts = date_str.split('-')
            if len(parts) == 3:
                year, month, day = parts
                if year.isdigit() and month.isdigit() and day.isdigit():
                    year, month, day = int(year), int(month), int(day)
                    if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                        return f"{year:04d}-{month:02d}-{day:02d}"
        
        # Формат DD.MM.YYYY
        if len(date_str) == 10 and date_str.count('.') == 2:
            parts = date_str.split('.')
            if len(parts) == 3:
                day, month, year = parts
                if day.isdigit() and month.isdigit() and year.isdigit():
                    day, month, year = int(day), int(month), int(year)
                    if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                        return f"{year:04d}-{month:02d}-{day:02d}"
        
        # Формат DD/MM/YYYY
        if len(date_str) == 10 and date_str.count('/') == 2:
            parts = date_str.split('/')
            if len(parts) == 3:
                day, month, year = parts
                if day.isdigit() and month.isdigit() and year.isdigit():
                    day, month, year = int(day), int(month), int(year)
                    if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                        return f"{year:04d}-{month:02d}-{day:02d}"
        
        return None
    except:
        return None

def acknowledge_feeding_notifications(fid):
    """Подтверждает уведомления о кормлении"""
    acknowledge_notification(fid, 'pre_feeding')
    acknowledge_notification(fid, 'regular_feeding')
    acknowledge_notification(fid, 'overdue_feeding')

def acknowledge_diaper_notifications(fid):
    """Подтверждает уведомления о смене подгузника"""
    acknowledge_notification(fid, 'pre_diaper')
    acknowledge_notification(fid, 'regular_diaper')
    acknowledge_notification(fid, 'overdue_diaper')

def handle_feeding_callback(event, minutes_ago):
    """Обрабатывает callback кормления"""
    uid = event.sender_id
    result = add_feeding(uid, minutes_ago)
    
    if result is True:
        fid = get_family_id(uid)
        if fid:
            acknowledge_feeding_notifications(fid)
        return True, "✅ Кормление записано!"
    elif result is False:
        fid = get_family_id(uid)
        if fid and check_recent_feeding(fid, 30):
            duplicate_confirmation_pending[uid] = {"action": "feeding", "minutes_ago": minutes_ago}
            return False, "⚠️ **Внимание!**\n\nКормление уже было записано в последние 30 минут.\n\nВы уверены, что хотите добавить еще одно кормление?", [[Button.inline("✅ Да, добавить", b"confirm_duplicate"), Button.inline("❌ Отмена", b"cancel_duplicate")]]
        else:
            return False, "❌ Ошибка записи кормления"
    else:
        return False, "❌ Ошибка записи кормления"

def handle_diaper_callback(event, minutes_ago):
    """Обрабатывает callback смены подгузника"""
    uid = event.sender_id
    result = add_diaper_change(uid, minutes_ago)
    
    if result is True:
        fid = get_family_id(uid)
        if fid:
            acknowledge_diaper_notifications(fid)
        return True, "✅ Смена подгузника записана!"
    elif result is False:
        fid = get_family_id(uid)
        if fid and check_recent_diaper_change(fid, 30):
            duplicate_confirmation_pending[uid] = {"action": "diaper", "minutes_ago": minutes_ago}
            return False, "⚠️ **Внимание!**\n\nСмена подгузника уже была записана в последние 30 минут.\n\nВы уверены, что хотите добавить еще одну смену?", [[Button.inline("✅ Да, добавить", b"confirm_duplicate"), Button.inline("❌ Отмена", b"cancel_duplicate")]]
        else:
            return False, "❌ Ошибка записи смены подгузника"
    else:
        return False, "❌ Ошибка записи смены подгузника"

def format_time_message(hours, minutes, event_type):
    """Форматирует сообщение о времени для кормления или смены подгузника"""
    if hours > 0:
        time_str = f"{hours}ч {minutes}м"
    else:
        time_str = f"{minutes}м"
    
    if event_type == "feeding":
        if hours == 0 and minutes < 30:
            return f"🍼 **Малыш недавно поел!**\n**{time_str} назад**\n\n"
        elif hours == 0:
            return f"🍼 **Последний раз кушали:**\n**{time_str} назад**\n\n"
        elif hours < 2:
            return f"🍼 **В последний раз кормили:**\n**{time_str} назад**\n\n"
        else:
            return f"🍼 **Последнее кормление было:**\n**{time_str} назад**\n\n"
    else:  # diaper
        if hours == 0 and minutes < 30:
            return f"🧷 **Подгузник свежий!**\n**{time_str} назад**\n\n"
        elif hours == 0:
            return f"🧷 **Последняя смена:**\n**{time_str} назад**\n\n"
        elif hours < 2:
            return f"🧷 **В последний раз меняли:**\n**{time_str} назад**\n\n"
        else:
            return f"🧷 **Последняя смена была:**\n**{time_str} назад**\n\n"

def calculate_next_time_message(hours, minutes, interval, event_type):
    """Вычисляет сообщение о времени до следующего события"""
    total_minutes_passed = hours * 60 + minutes
    total_interval_minutes = interval * 60
    remaining_minutes = total_interval_minutes - total_minutes_passed
    
    next_hours = remaining_minutes // 60
    next_minutes = remaining_minutes % 60
    
    if next_hours > 0:
        next_time_str = f"{next_hours}ч {next_minutes}м"
    else:
        next_time_str = f"{next_minutes}м"
    
    if event_type == "feeding":
        return f"⏰ **До следующего кормления:**\n**{next_time_str}**\n\n"
    else:  # diaper
        return f"⏰ **До следующей смены:**\n**{next_time_str}**\n\n"


# Функция для внешнего keep-alive (для Replit)
def external_keep_alive():
    """Функция для внешнего keep-alive через Replit"""
    try:
        import urllib.request
        import urllib.error
        
        # Получаем внешний URL из переменных окружения
        external_url = REPLIT_EXTERNAL_URL
        if external_url:
            # Убираем trailing slash если есть
            if external_url.endswith('/'):
                external_url = external_url[:-1]
            
            # Пингуем внешний URL
            try:
                response = urllib.request.urlopen(f'{external_url}/ping', timeout=10)
                if response.getcode() == 200:
                    print(f"✅ External keep-alive successful: {time.strftime('%H:%M:%S')}")
                else:
                    print(f"⚠️ External keep-alive returned status: {response.getcode()}")
            except urllib.error.URLError as e:
                print(f"⚠️ External keep-alive failed: {e}")
            except Exception as e:
                print(f"⚠️ External keep-alive error: {e}")
        else:
            print("ℹ️ External URL not set, skipping external keep-alive")
            
    except Exception as e:
        print(f"❌ External keep-alive critical error: {e}")

init_supabase()
scheduler = AsyncIOScheduler()

def keep_alive_ping():
    """Функция для поддержания активности бота"""
    try:
        print(f"💓 Keep-alive ping: {time.strftime('%H:%M:%S')}")
        
        # Проверяем подключение к Supabase
        if test_connection():
            print("✅ Supabase connection OK")
        else:
            print("❌ Supabase connection failed")
            
    except Exception as e:
        print(f"❌ Keep-alive ping critical error: {e}")

telegram_client = None
reminder_queue = []  # Очередь для напоминаний

def send_smart_reminders():
    """Отправка напоминаний всем семьям"""
    global telegram_client, reminder_queue
    
    if not telegram_client:
        print("⚠️ Telegram client not available for reminders")
        return
    
    try:
        print(f"🔔 Checking smart reminders: {time.strftime('%H:%M:%S')}")
        
        # Получаем все семьи
        families = get_all_families()
        print(f"🔔 Found {len(families)} families to check")
        
        if not families:
            print("🔔 No families found in database")
            return
        
        for family_id in families:
            try:
                print(f"🔔 Checking family {family_id}")
                
                # Проверяем предварительные напоминания (за 5 минут)
                pre_conditions = check_pre_reminder_conditions(family_id)
                print(f"🔔 Family {family_id} - pre_feeding: {pre_conditions['needs_pre_feeding']}, pre_diaper: {pre_conditions['needs_pre_diaper']}")
                
                if pre_conditions['needs_pre_feeding'] or pre_conditions['needs_pre_diaper']:
                    print(f"🔔 Family {family_id} - needs pre-reminder!")
                    
                    # Проверяем, не отправляли ли мы уже предварительные уведомления недавно
                    # Также проверяем, что не отправляли обычные или просроченные уведомления
                    should_send_pre_feeding = (pre_conditions['needs_pre_feeding'] and 
                                             not check_recent_notification(family_id, 'pre_feeding', 5) and
                                             not check_recent_notification(family_id, 'regular_feeding', 10) and
                                             not check_recent_notification(family_id, 'overdue_feeding', 10))
                    should_send_pre_diaper = (pre_conditions['needs_pre_diaper'] and 
                                            not check_recent_notification(family_id, 'pre_diaper', 5) and
                                            not check_recent_notification(family_id, 'regular_diaper', 10) and
                                            not check_recent_notification(family_id, 'overdue_diaper', 10))
                    
                    if should_send_pre_feeding or should_send_pre_diaper:
                        # Получаем сообщение предварительного напоминания
                        message = get_pre_reminder_message(family_id)
                        if message:
                            # Получаем членов семьи для отправки уведомлений
                            members = get_family_members_for_notification(family_id)
                            
                            if members:
                                # Создаем кнопки для быстрых действий
                                buttons = []
                                if should_send_pre_feeding:
                                    buttons.append([Button.inline("🍼 Отметить кормление", b"feed_now")])
                                if should_send_pre_diaper:
                                    buttons.append([Button.inline("💩 Смена подгузника", b"diaper_now")])
                                
                                # Добавляем предварительные напоминания в очередь
                                for user_id in members:
                                    reminder_queue.append({
                                        'user_id': user_id,
                                        'message': message,
                                        'buttons': buttons,
                                        'notification_type': 'pre_feeding' if should_send_pre_feeding else 'pre_diaper',
                                        'family_id': family_id
                                    })
                                    print(f"🔔 Added pre-reminder to queue for user {user_id}")
                                
                                # Логируем отправку уведомления
                                if should_send_pre_feeding:
                                    log_notification_sent(family_id, 'pre_feeding', get_thai_time())
                                if should_send_pre_diaper:
                                    log_notification_sent(family_id, 'pre_diaper', get_thai_time())
                
                # Проверяем просроченные напоминания (через 15 минут после времени)
                overdue_conditions = check_overdue_reminder_conditions(family_id)
                print(f"🔔 Family {family_id} - overdue_feeding: {overdue_conditions['needs_overdue_feeding']}, overdue_diaper: {overdue_conditions['needs_overdue_diaper']}")
                
                if overdue_conditions['needs_overdue_feeding'] or overdue_conditions['needs_overdue_diaper']:
                    print(f"🔔 Family {family_id} - needs overdue reminder!")
                    
                    # Проверяем, не отправляли ли мы уже просроченные уведомления недавно
                    # Также проверяем, что не отправляли предварительные или обычные уведомления
                    should_send_overdue_feeding = (overdue_conditions['needs_overdue_feeding'] and 
                                                 not check_recent_notification(family_id, 'overdue_feeding', 15) and
                                                 not check_recent_notification(family_id, 'pre_feeding', 10) and
                                                 not check_recent_notification(family_id, 'regular_feeding', 10))
                    should_send_overdue_diaper = (overdue_conditions['needs_overdue_diaper'] and 
                                                not check_recent_notification(family_id, 'overdue_diaper', 15) and
                                                not check_recent_notification(family_id, 'pre_diaper', 10) and
                                                not check_recent_notification(family_id, 'regular_diaper', 10))
                    
                    if should_send_overdue_feeding or should_send_overdue_diaper:
                        # Получаем сообщение просроченного напоминания
                        message = get_overdue_reminder_message(family_id)
                        if message:
                            # Получаем членов семьи для отправки уведомлений
                            members = get_family_members_for_notification(family_id)
                            
                            if members:
                                # Создаем кнопки для быстрых действий
                                buttons = []
                                if should_send_overdue_feeding:
                                    buttons.append([Button.inline("🍼 Отметить кормление", b"feed_now")])
                                if should_send_overdue_diaper:
                                    buttons.append([Button.inline("💩 Смена подгузника", b"diaper_now")])
                                
                                # Добавляем просроченные напоминания в очередь
                                for user_id in members:
                                    reminder_queue.append({
                                        'user_id': user_id,
                                        'message': message,
                                        'buttons': buttons,
                                        'notification_type': 'overdue_feeding' if should_send_overdue_feeding else 'overdue_diaper',
                                        'family_id': family_id
                                    })
                                    print(f"🔔 Added overdue reminder to queue for user {user_id}")
                                
                                # Логируем отправку уведомления
                                if should_send_overdue_feeding:
                                    log_notification_sent(family_id, 'overdue_feeding', get_thai_time())
                                if should_send_overdue_diaper:
                                    log_notification_sent(family_id, 'overdue_diaper', get_thai_time())
                
                # Проверяем обычные напоминания (когда время пришло)
                conditions = check_smart_reminder_conditions(family_id)
                print(f"🔔 Family {family_id} - needs_feeding: {conditions['needs_feeding']}, needs_diaper: {conditions['needs_diaper']}")
                
                if conditions['needs_feeding'] or conditions['needs_diaper']:
                    print(f"🔔 Family {family_id} - needs regular reminder!")
                    
                    # Проверяем, не отправляли ли мы уже обычные уведомления недавно
                    # Также проверяем, что не отправляли предварительные или просроченные уведомления
                    should_send_regular_feeding = (conditions['needs_feeding'] and 
                                                 not check_recent_notification(family_id, 'regular_feeding', 30) and
                                                 not check_recent_notification(family_id, 'pre_feeding', 10) and
                                                 not check_recent_notification(family_id, 'overdue_feeding', 10))
                    should_send_regular_diaper = (conditions['needs_diaper'] and 
                                                not check_recent_notification(family_id, 'regular_diaper', 30) and
                                                not check_recent_notification(family_id, 'pre_diaper', 10) and
                                                not check_recent_notification(family_id, 'overdue_diaper', 10))
                    
                    if should_send_regular_feeding or should_send_regular_diaper:
                        # Получаем сообщение напоминания
                        message = get_smart_reminder_message(family_id)
                        if message:
                            # Получаем членов семьи для отправки уведомлений
                            members = get_family_members_for_notification(family_id)
                            
                            if members:
                                # Создаем кнопки для быстрых действий
                                buttons = []
                                if should_send_regular_feeding:
                                    buttons.append([Button.inline("🍼 Отметить кормление", b"feed_now")])
                                if should_send_regular_diaper:
                                    buttons.append([Button.inline("💩 Смена подгузника", b"diaper_now")])
                                
                                # Добавляем обычные напоминания в очередь
                                for user_id in members:
                                    reminder_queue.append({
                                        'user_id': user_id,
                                        'message': message,
                                        'buttons': buttons,
                                        'notification_type': 'regular_feeding' if should_send_regular_feeding else 'regular_diaper',
                                        'family_id': family_id
                                    })
                                    print(f"🔔 Added regular reminder to queue for user {user_id}")
                                
                                # Логируем отправку уведомления
                                if should_send_regular_feeding:
                                    log_notification_sent(family_id, 'regular_feeding', get_thai_time())
                                if should_send_regular_diaper:
                                    log_notification_sent(family_id, 'regular_diaper', get_thai_time())
                
                print(f"✅ All reminders checked for family {family_id}")
                
            except Exception as e:
                print(f"❌ Ошибка обработки семьи {family_id}: {e}")
                continue
                
    except Exception as e:
        print(f"❌ Critical error in smart reminders: {e}")

async def send_reminder_message(user_id: int, message: str, buttons: list):
    """Асинхронная отправка сообщения напоминания"""
    global telegram_client
    
    if not telegram_client:
        return
    
    try:
        await telegram_client.send_message(user_id, message, buttons=buttons)
    except Exception as e:
        print(f"❌ Ошибка отправки сообщения пользователю {user_id}: {e}")

async def process_reminder_queue():
    """Обработка очереди напоминаний"""
    global reminder_queue, telegram_client
    
    if not telegram_client or not reminder_queue:
        return
    
    print(f"📤 Processing {len(reminder_queue)} reminders from queue...")
    
    # Обрабатываем все напоминания в очереди
    while reminder_queue:
        reminder = reminder_queue.pop(0)
        try:
            await send_reminder_message(
                reminder['user_id'], 
                reminder['message'], 
                reminder['buttons']
            )
            print(f"✅ Reminder sent to user {reminder['user_id']}")
        except Exception as e:
            print(f"❌ Ошибка отправки напоминания пользователю {reminder['user_id']}: {e}")

scheduler.add_job(keep_alive_ping, 'interval', minutes=5, id='keep_alive_ping')
print("⏰ Keep-alive ping scheduled every 5 minutes")

scheduler.add_job(send_smart_reminders, 'interval', minutes=5, id='smart_reminders')
print("⏰ Smart reminders scheduled every 5 minutes")

def process_reminder_queue_sync():
    """Синхронная обработка очереди напоминаний"""
    global reminder_queue
    if reminder_queue:
        print(f"📤 Found {len(reminder_queue)} reminders in queue")
        # Обработка будет происходить в главном цикле бота

scheduler.add_job(process_reminder_queue_sync, 'interval', minutes=1, id='process_reminders')
print("⏰ Reminder queue processing scheduled every 1 minute")


scheduler.add_job(external_keep_alive, 'interval', minutes=3, id='external_keep_alive')
print("⏰ External keep-alive scheduled every 3 minutes")

def cleanup_notifications():
    """Очистка старых записей уведомлений"""
    try:
        print(f"🧹 Cleaning up old notifications: {time.strftime('%H:%M:%S')}")
        cleanup_old_notifications(7)  # Удаляем записи старше 7 дней
        print("✅ Old notifications cleaned up")
    except Exception as e:
        print(f"❌ Error cleaning up notifications: {e}")

scheduler.add_job(cleanup_notifications, 'interval', hours=24, id='cleanup_notifications')
print("⏰ Notification cleanup scheduled every 24 hours")

family_creation_pending = {}
manual_feeding_pending = {}
join_pending = {}
edit_pending = {}
edit_role_pending = {}
bath_pending = {}
activity_pending = {}
baby_birth_pending = {}
custom_time_pending = {}
duplicate_confirmation_pending = {}  # Для подтверждения дубликатов

def is_port_available(port):
    """Проверяет, доступен ли порт"""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', port))
            return True
    except OSError:
        return False

def start_health_server(port=8001):
    """Запуск HTTP сервера для health checks"""
    class HealthHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/ping':
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'pong')
            else:
                self.send_response(404)
                self.end_headers()
    
    # Пытаемся найти свободный порт
    for attempt in range(10):
        if is_port_available(port):
            try:
                with socketserver.TCPServer(("", port), HealthHandler) as httpd:
                    print(f"🏥 Health server started on port {port}")
                    httpd.serve_forever()
                break
            except Exception as e:
                print(f"❌ Health server error on port {port}: {e}")
                port += 1
                continue
        else:
            print(f"⚠️ Port {port} is busy, trying port {port+1}...")
            port += 1
    else:
        print("❌ Could not find available port for health server")

async def start_bot():
    """Запуск бота"""
    global telegram_client
    print("🚀 Запуск BabyCareBot...")
    
    try:
        # Создаем клиент Telegram
        print("📱 Создаем Telegram клиент...")
        client = TelegramClient('babybot', API_ID, API_HASH)
        
        print("🔄 Подключаемся к Telegram...")
        await client.start(bot_token=BOT_TOKEN)
        
        # Получаем информацию о боте
        me = await client.get_me()
        print(f"✅ Бот подключен: @{me.username} ({me.first_name})")
        
        # Сохраняем клиент в глобальной переменной для напоминаний
        telegram_client = client
        print("✅ Telegram клиент сохранен для напоминаний")
        
    except Exception as e:
        print(f"❌ Ошибка подключения к Telegram: {e}")
        return
    
    # Небольшая задержка для стабилизации подключения
    await asyncio.sleep(1)
    
    # Запускаем health server в отдельном потоке
    try:
        health_thread = threading.Thread(target=start_health_server, daemon=True)
        health_thread.start()
        print("✅ Health server thread started")
    except Exception as e:
        print(f"⚠️ Health server not started: {e}")
        print("ℹ️ Bot will continue without health server")
    
    # Запускаем планировщик
    scheduler.start()
    print("⏰ Планировщик запущен")
    
    # Регистрируем обработчики событий
    @client.on(events.NewMessage(pattern='/start'))
    async def start(event):
        uid = event.sender_id
        fid = get_family_id(uid)
        
        if fid:
            # Пользователь уже в семье
            family_name = get_family_name(fid)
            role, name = get_member_info(uid)
            
            welcome_message = (
                f"👶 **Добро пожаловать в BabyCareBot!**\n\n"
                f"🏠 **Ваша семья:** {family_name}\n"
                f"👤 **Ваша роль:** {role} {name}\n\n"
                f"💡 Я помогу следить за малышом и координировать уход в семье!\n\n"
                f"📊 **Дашборд:** https://bcb-db.vercel.app"
            )
        else:
            # Пользователь не в семье
            welcome_message = (
                f"👶 **Добро пожаловать в BabyCareBot!**\n\n"
                f"🎯 **Что я умею:**\n"
                f"• 🍼 Отслеживать и записывать кормления\n"
                f"• 🧷 Записывать смены подгузников\n"
                f"• 🛁 Напоминания о купании (настраиваются в настройках)\n"
                f"• 🎮 Напоминания об играх и активности (настраиваются в настройках)\n"
                f"• 📊 Показывать историю и статистику\n"
                f"• ⏰ Напоминать о важных событиях\n"
                f"• 👥 Координировать уход в семье\n\n"
                f"🚀 **Для начала работы:**\n"
                f"1️⃣ Создайте семью или присоединитесь к существующей\n"
                f"2️⃣ Настройте интервалы кормления и смены подгузников\n"
                f"3️⃣ Начните отслеживать активность малыша\n\n"
                f"📊 **Дашборд:** https://bcb-db.vercel.app"
            )
        
        # Проверяем, есть ли у пользователя семья
        uid = event.sender_id
        fid = get_family_id(uid)
        
        if fid:
            # Пользователь уже в семье - показываем основные функции
            buttons = [
                [Button.text("🍼 Кормление"), Button.text("💩 Смена подгузника")],
                [Button.text("💡 Советы"), Button.text("⚙️ Настройки")]
            ]
        else:
            # Пользователь не в семье - показываем кнопки создания/присоединения
            buttons = [
                [Button.text("👨‍👩‍👧 Создать семью"), Button.text("🔗 Присоединиться")]
            ]
        
        await event.respond(welcome_message, buttons=buttons)
    
    @client.on(events.NewMessage(pattern='🍼 Кормление'))
    async def feeding_menu(event):
        """Показать статус кормления с возможностью отметить кормление"""
        uid = event.sender_id
        fid = get_family_id(uid)
        
        if not fid:
            await event.respond("❌ Вы не состоите в семье. Сначала создайте семью или присоединитесь к существующей.")
            return
        
        # Получаем время последнего кормления
        last_feeding = get_last_feeding_time_for_family(fid)
        
        if last_feeding:
            # Вычисляем время с последнего кормления
            now = get_thai_time()
            time_diff = now - last_feeding
            hours = int(time_diff.total_seconds() // 3600)
            minutes = int((time_diff.total_seconds() % 3600) // 60)
            
            if hours > 0:
                time_str = f"{hours}ч {minutes}м"
            else:
                time_str = f"{minutes}м"
            
            # Создаем более живые сообщения в зависимости от времени
            if hours == 0 and minutes < 30:
                message = f"🍼 **Малыш недавно поел!**\n**{time_str} назад**\n\n"
            elif hours == 0:
                message = f"🍼 **Последний раз кушали:**\n**{time_str} назад**\n\n"
            elif hours < 2:
                message = f"🍼 **В последний раз кормили:**\n**{time_str} назад**\n\n"
            else:
                message = f"🍼 **Последнее кормление было:**\n**{time_str} назад**\n\n"
            
            # Проверяем, нужно ли напоминание
            feed_interval, _ = get_user_intervals(fid)
            
            if hours >= feed_interval:


                message += f"🍽️ **Время обеда!** Малыш проголодался! (интервал: {feed_interval}ч) 🥄\n\n"
            else:
                # Правильный расчет времени до следующего кормления
                total_minutes_passed = hours * 60 + minutes
                total_interval_minutes = feed_interval * 60
                remaining_minutes = total_interval_minutes - total_minutes_passed
                
                next_hours = remaining_minutes // 60
                next_minutes = remaining_minutes % 60
                
                if next_hours > 0:
                    next_time_str = f"{next_hours}ч {next_minutes}м"
                else:
                    next_time_str = f"{next_minutes}м"
                message += f"⏰ **До следующего кормления:**\n**{next_time_str}**\n\n"
        else:
            message = "🍼 **Добро пожаловать!** Начнем отслеживать кормления малыша! 👶✨\n\n"
        
        message += "🍼 **Отметить еду:**"
        
        buttons = [
            [Button.inline("✅ Сейчас", b"feed_now"), Button.inline("⏰ 15 мин назад", b"feed_15min")],
            [Button.inline("⏰ 30 мин назад", b"feed_30min"), Button.inline("🕐 Указать время", b"feed_custom_time")]
        ]
        
        await event.respond(message, buttons=buttons)
    
    @client.on(events.NewMessage(pattern='💩 Смена подгузника'))
    async def diaper_menu(event):
        """Показать статус смены подгузника с возможностью отметить смену"""
        uid = event.sender_id
        fid = get_family_id(uid)
        
        if not fid:
            await event.respond("❌ Вы не состоите в семье. Сначала создайте семью или присоединитесь к существующей.")
            return
        
        # Получаем время последней смены подгузника
        last_diaper = get_last_diaper_change_time_for_family(fid)
        
        if last_diaper:
            # Вычисляем время с последней смены
            now = get_thai_time()
            time_diff = now - last_diaper
            hours = int(time_diff.total_seconds() // 3600)
            minutes = int((time_diff.total_seconds() % 3600) // 60)
            
            if hours > 0:
                time_str = f"{hours}ч {minutes}м"
            else:
                time_str = f"{minutes}м"
            
            # Создаем более живые сообщения для смены подгузников
            if hours == 0 and minutes < 30:
                message = f"🧷 **Подгузник свежий!**\n**{time_str} назад**\n\n"
            elif hours == 0:
                message = f"🧷 **Последняя смена:**\n**{time_str} назад**\n\n"
            elif hours < 2:
                message = f"🧷 **В последний раз меняли:**\n**{time_str} назад**\n\n"
            else:
                message = f"🧷 **Последняя смена была:**\n**{time_str} назад**\n\n"
            
            # Проверяем, нужно ли напоминание
            _, diaper_interval = get_user_intervals(fid)
            
            if hours >= diaper_interval:
                message += f"🔄 **Время менять!** Малышу нужен свежий подгузник! (интервал: {diaper_interval}ч) 🧴\n\n"
            else:
                # Правильный расчет времени до следующей смены подгузника
                total_minutes_passed = hours * 60 + minutes
                total_interval_minutes = diaper_interval * 60
                remaining_minutes = total_interval_minutes - total_minutes_passed
                
                next_hours = remaining_minutes // 60
                next_minutes = remaining_minutes % 60
                
                if next_hours > 0:
                    next_time_str = f"{next_hours}ч {next_minutes}м"
                else:
                    next_time_str = f"{next_minutes}м"
                message += f"⏰ **До следующей смены:**\n**{next_time_str}**\n\n"
        else:
            message = "🧷 **Добро пожаловать!** Начнем отслеживать смены подгузников! 👶✨\n\n"
        
        message += "💩 **Отметить смену подгузника:**"
        
        buttons = [
            [Button.inline("✅ Сейчас", b"diaper_now"), Button.inline("⏰ 15 мин назад", b"diaper_15min")],
            [Button.inline("⏰ 30 мин назад", b"diaper_30min"), Button.inline("🕐 Указать время", b"diaper_custom_time")]
        ]
        
        await event.respond(message, buttons=buttons)
    
    @client.on(events.NewMessage(pattern='💡 Советы'))
    async def tips_menu(event):
        """Показать случайный совет"""
        uid = event.sender_id
        fid = get_family_id(uid)
        
        if not fid:
            await event.respond("❌ Вы не состоите в семье. Сначала создайте семью или присоединитесь к существующей.")
            return
        
        # Получаем возраст малыша и случайный совет
        age_months = get_baby_age_months(fid)
        tip = get_random_tip(age_months)
        
        if tip:
            message = f"💡 **Совет для {age_months} месяцев:**\n\n{tip}"
        else:
            message = "💡 Советов для вашего возраста пока нет. Попробуйте позже!"
        
        await event.respond(message)
    
    
    @client.on(events.NewMessage(pattern='⚙️ Настройки'))
    async def settings_menu(event):
        """Показать настройки"""
        uid = event.sender_id
        fid = get_family_id(uid)
        
        if not fid:
            await event.respond("❌ Вы не состоите в семье. Сначала создайте семью или присоединитесь к существующей.")
            return
        
        # Получаем настройки и статистику
        settings = get_notification_settings(fid)
        intervals = get_user_intervals(fid)
        feeding_stats = get_feeding_stats(fid)
        diaper_stats = get_diaper_stats(fid)
        bath_stats = get_bath_stats(fid)
        activity_stats = get_activity_stats(fid)
        birth_date = get_birth_date(fid)
        
        message = "⚙️ **Настройки и статистика:**\n\n"
        
        # Статистика за сегодня
        message += "📊 **Статистика за сегодня:**\n"
        if feeding_stats:
            message += f"🍼 Кормления: {feeding_stats['count']} раз\n"
        if diaper_stats:
            message += f"💩 Смены подгузников: {diaper_stats['count']} раз\n"
        if bath_stats:
            message += f"🛁 Купания: {bath_stats['count']} раз\n"
        if activity_stats:
            message += f"🎮 Активность: {activity_stats['count']} раз\n"
        
        message += "\n⚙️ **Текущие настройки:**\n"
        
        if intervals:
            feed_interval, diaper_interval = intervals
            message += f"🍼 Интервал кормления: {feed_interval}ч\n"
            message += f"💩 Интервал смены подгузника: {diaper_interval}ч\n\n"
        
        if settings:
            message += f"💡 Советы: {'Включены' if settings.get('tips_enabled') else 'Выключены'}\n"
            message += f"🛁 Напоминания о купании: {'Включены' if settings.get('bath_reminder_enabled') else 'Выключены'}\n"
            message += f"🎮 Напоминания об активности: {'Включены' if settings.get('activity_reminder_enabled') else 'Выключены'}\n"
        
        if birth_date:
            message += f"📅 Дата рождения малыша: {birth_date}\n"
        else:
            message += f"📅 Дата рождения малыша: Не установлена\n"
        
        message += "\n🎯 **Что настроим?**"
        
        buttons = [
            [Button.inline("🍼 Интервал кормления", b"settings_feeding"), Button.inline("💩 Интервал подгузников", b"settings_diaper")],
            [Button.inline("💡 Советы", b"settings_tips"), Button.inline("🛁 Купание", b"settings_bath")],
            [Button.inline("🎮 Активность", b"settings_activity"), Button.inline("⏰ Время уведомлений", b"settings_time")],
            [Button.inline("📅 Дата рождения", b"settings_birth_date"), Button.inline("🔙 Назад", b"back_to_main")]
        ]
        
        await event.respond(message, buttons=buttons)
    
    @client.on(events.CallbackQuery)
    async def callback_handler(event):
        data = event.data.decode()
        uid = event.sender_id
        
        print(f"DEBUG: Callback data: {data} for user {uid}")
        
        # Обработка кнопок кормления
        if data == "feed_now":
            success, message = handle_feeding_callback(event, 0)
            if success:
                await event.edit(message)
            else:
                if isinstance(message, tuple):
                    await event.edit(message[0], buttons=message[1])
                else:
                    await event.edit(message)
        
        elif data == "feed_15min":
            success, message = handle_feeding_callback(event, 15)
            if success:
                await event.edit(message)
            else:
                if isinstance(message, tuple):
                    await event.edit(message[0], buttons=message[1])
                else:
                    await event.edit(message)
        
        elif data == "feed_30min":
            success, message = handle_feeding_callback(event, 30)
            if success:
                await event.edit(message)
            else:
                if isinstance(message, tuple):
                    await event.edit(message[0], buttons=message[1])
                else:
                    await event.edit(message)
        
        # Обработка кнопок смены подгузника
        elif data == "diaper_now":
            success, message = handle_diaper_callback(event, 0)
            if success:
                await event.edit(message)
            else:
                if isinstance(message, tuple):
                    await event.edit(message[0], buttons=message[1])
                else:
                    await event.edit(message)
        
        elif data == "diaper_15min":
            success, message = handle_diaper_callback(event, 15)
            if success:
                await event.edit(message)
            else:
                if isinstance(message, tuple):
                    await event.edit(message[0], buttons=message[1])
                else:
                    await event.edit(message)
        
        elif data == "diaper_30min":
            success, message = handle_diaper_callback(event, 30)
            if success:
                await event.edit(message)
            else:
                if isinstance(message, tuple):
                    await event.edit(message[0], buttons=message[1])
                else:
                    await event.edit(message)
        
        # Обработка подтверждения дубликатов
        elif data == "confirm_duplicate":
            if uid in duplicate_confirmation_pending:
                pending_data = duplicate_confirmation_pending[uid]
                action = pending_data["action"]
                minutes_ago = pending_data["minutes_ago"]
                
                if action == "feeding":
                    if add_feeding(uid, minutes_ago, force=True):
                        fid = get_family_id(uid)
                        if fid:
                            acknowledge_feeding_notifications(fid)
                        await event.edit("✅ Кормление записано!")
                    else:
                        await event.edit("❌ Ошибка записи кормления")
                elif action == "diaper":
                    if add_diaper_change(uid, minutes_ago, force=True):
                        fid = get_family_id(uid)
                        if fid:
                            acknowledge_diaper_notifications(fid)
                        await event.edit("✅ Смена подгузника записана!")
                    else:
                        await event.edit("❌ Ошибка записи смены подгузника")
                
                del duplicate_confirmation_pending[uid]
            else:
                await event.edit("❌ Ошибка: данные подтверждения не найдены")
        
        elif data == "cancel_duplicate":
            if uid in duplicate_confirmation_pending:
                del duplicate_confirmation_pending[uid]
                await event.edit("❌ Операция отменена")
            else:
                await event.edit("❌ Ошибка: данные подтверждения не найдены")
        
        # Обработка кнопки "Назад"
        elif data == "back_to_main":
            fid = get_family_id(uid)
            if fid:
                family_name = get_family_name(fid)
                role, name = get_member_info(uid)
                
                message = (
                    f"👶 **BabyCareBot**\n\n"
                    f"🏠 **Семья:** {family_name}\n"
                    f"👤 **Роль:** {role} {name}\n\n"
                    f"🎯 **Что делаем?**"
                )
            else:
                message = (
                    f"👶 **BabyCareBot**\n\n"
                    f"🎯 **Что делаем?**"
                )
            
            buttons = [
                [Button.text("🍼 Кормление"), Button.text("💩 Смена подгузника")],
                [Button.text("💡 Советы"), Button.text("⚙️ Настройки")]
            ]
            
            await event.edit(message, buttons=buttons)
        
        
        # Обработка кнопок "Указать время"
        elif data == "feed_custom_time":
            custom_time_pending[uid] = "feeding"
            await event.edit("🕐 **Укажите время кормления**\n\nВведите время в формате:\n• **15** (15 минут назад)\n• **1:30** (1 час 30 минут назад)\n• **2ч** (2 часа назад)")
        
        elif data == "diaper_custom_time":
            custom_time_pending[uid] = "diaper"
            await event.edit("🕐 **Укажите время смены подгузника**\n\nВведите время в формате:\n• **15** (15 минут назад)\n• **1:30** (1 час 30 минут назад)\n• **2ч** (2 часа назад)")
        
        # Обработка настроек
        elif data == "settings_feeding":
            fid = get_family_id(uid)
            if fid:
                intervals = get_user_intervals(fid)
                current_interval = intervals[0] if intervals else 3
                
                message = f"🍼 **Интервал кормления:** {current_interval} часов\n\nВыберите новый интервал:"
                
                buttons = [
                    [Button.inline("3 часа", b"set_feed_3"), Button.inline("4 часа", b"set_feed_4")],
                    [Button.inline("5 часов", b"set_feed_5"), Button.inline("6 часов", b"set_feed_6")],
                    [Button.inline("🔙 Назад к настройкам", b"back_to_settings")]
                ]
                
                await event.edit(message, buttons=buttons)
            else:
                await event.edit("❌ Ошибка получения настроек")
        
        elif data == "settings_diaper":
            fid = get_family_id(uid)
            if fid:
                intervals = get_user_intervals(fid)
                current_interval = intervals[1] if intervals else 2
                
                message = f"💩 **Интервал смены подгузника:** {current_interval} часов\n\nВыберите новый интервал:"
                
                buttons = [
                    [Button.inline("2 часа", b"set_diaper_2"), Button.inline("3 часа", b"set_diaper_3")],
                    [Button.inline("4 часа", b"set_diaper_4"), Button.inline("5 часов", b"set_diaper_5")],
                    [Button.inline("🔙 Назад к настройкам", b"back_to_settings")]
                ]
                
                await event.edit(message, buttons=buttons)
            else:
                await event.edit("❌ Ошибка получения настроек")
        
        elif data == "settings_tips":
            fid = get_family_id(uid)
            if fid:
                settings = get_notification_settings(fid)
                tips_enabled = settings.get('tips_enabled', True) if settings else True
                
                message = f"💡 **Советы:** {'Включены' if tips_enabled else 'Выключены'}\n\n🎯 **Что делаем?**"
                
                buttons = [
                    [Button.inline("✅ Включить", b"toggle_tips_on"), Button.inline("❌ Выключить", b"toggle_tips_off")],
                    [Button.inline("🔙 Назад к настройкам", b"back_to_settings")]
                ]
                
                await event.edit(message, buttons=buttons)
            else:
                await event.edit("❌ Ошибка получения настроек")
        
        elif data == "settings_bath":
            fid = get_family_id(uid)
            if fid:
                settings = get_notification_settings(fid)
                bath_enabled = settings.get('bath_reminder_enabled', True) if settings else True
                
                message = f"🛁 **Напоминания о купании:** {'Включены' if bath_enabled else 'Выключены'}\n\n🎯 **Что делаем?**"
                
                buttons = [
                    [Button.inline("✅ Включить", b"toggle_bath_on"), Button.inline("❌ Выключить", b"toggle_bath_off")],
                    [Button.inline("🔙 Назад к настройкам", b"back_to_settings")]
                ]
                
                await event.edit(message, buttons=buttons)
            else:
                await event.edit("❌ Ошибка получения настроек")
        
        elif data == "settings_activity":
            fid = get_family_id(uid)
            if fid:
                settings = get_notification_settings(fid)
                activity_enabled = settings.get('activity_reminder_enabled', True) if settings else True
                
                message = f"🎮 **Напоминания об активности:** {'Включены' if activity_enabled else 'Выключены'}\n\n🎯 **Что делаем?**"
                
                buttons = [
                    [Button.inline("✅ Включить", b"toggle_activity_on"), Button.inline("❌ Выключить", b"toggle_activity_off")],
                    [Button.inline("🔙 Назад к настройкам", b"back_to_settings")]
                ]
                
                await event.edit(message, buttons=buttons)
            else:
                await event.edit("❌ Ошибка получения настроек")
        
        elif data == "settings_time":
            fid = get_family_id(uid)
            if fid:
                settings = get_notification_settings(fid)
                tips_hour = settings.get('tips_time_hour', 9)
                tips_minute = settings.get('tips_time_minute', 0)
                bath_hour = settings.get('bath_reminder_hour', 19)
                bath_minute = settings.get('bath_reminder_minute', 0)
                activity_interval = settings.get('activity_reminder_interval', 2)
                
                message = f"⏰ **Настройки времени уведомлений:**\n\n"
                message += f"💡 **Советы:** {tips_hour:02d}:{tips_minute:02d}\n"
                message += f"🛁 **Купание:** {bath_hour:02d}:{bath_minute:02d}\n"
                message += f"🎮 **Активность:** каждые {activity_interval}ч\n\n"
                message += f"🎯 **Что настроим?**"
                
                buttons = [
                    [Button.inline("💡 Время советов", b"set_tips_time"), Button.inline("🛁 Время купания", b"set_bath_time")],
                    [Button.inline("🎮 Интервал активности", b"set_activity_interval")],
                    [Button.inline("🔙 Назад к настройкам", b"back_to_settings")]
                ]
                
                await event.edit(message, buttons=buttons)
            else:
                await event.edit("❌ Ошибка получения настроек")
        
        elif data == "settings_birth_date":
            fid = get_family_id(uid)
            if fid:
                birth_date = get_birth_date(fid)
                
                message = f"📅 **Настройка даты рождения малыша:**\n\n"
                if birth_date:
                    message += f"📅 **Текущая дата:** {birth_date}\n\n"
                else:
                    message += f"📅 **Дата не установлена**\n\n"
                
                message += f"🎯 **Что делаем?**"
                
                buttons = [
                    [Button.inline("📅 Установить дату", b"set_birth_date")],
                    [Button.inline("🔙 Назад к настройкам", b"back_to_settings")]
                ]
                
                await event.edit(message, buttons=buttons)
            else:
                await event.edit("❌ Ошибка получения настроек")
        
        # Обработка изменения интервалов
        elif data.startswith("set_feed_"):
            interval = int(data.split("_")[2])
            fid = get_family_id(uid)
            if fid and set_user_interval(fid, interval, None):
                await event.edit(f"✅ Интервал кормления изменен на {interval} часов!")
            else:
                await event.edit("❌ Ошибка изменения интервала")
        
        elif data.startswith("set_diaper_"):
            interval = int(data.split("_")[2])
            fid = get_family_id(uid)
            if fid and set_user_interval(fid, None, interval):
                await event.edit(f"✅ Интервал смены подгузника изменен на {interval} часов!")
            else:
                await event.edit("❌ Ошибка изменения интервала")
        
        elif data.startswith("set_activity_"):
            interval = int(data.split("_")[2])
            fid = get_family_id(uid)
            if fid and update_notification_settings(fid, {"activity_reminder_interval": interval}):
                await event.edit(f"✅ Интервал активности изменен на {interval} часов!")
            else:
                await event.edit("❌ Ошибка изменения интервала")
        
        # Обработка настройки времени
        elif data == "set_tips_time":
            custom_time_pending[uid] = "tips_time"
            await event.edit("💡 **Настройка времени советов**\n\nВведите время в формате:\n• **9:00** (9 часов 0 минут)\n• **14:30** (14 часов 30 минут)\n• **21** (21 час 0 минут)")
        
        elif data == "set_bath_time":
            custom_time_pending[uid] = "bath_time"
            await event.edit("🛁 **Настройка времени купания**\n\nВведите время в формате:\n• **19:00** (19 часов 0 минут)\n• **20:30** (20 часов 30 минут)\n• **21** (21 час 0 минут)")
        
        elif data == "set_activity_interval":
            fid = get_family_id(uid)
            if fid:
                settings = get_notification_settings(fid)
                current_interval = settings.get('activity_reminder_interval', 2)
                
                message = f"🎮 **Интервал напоминаний об активности:** {current_interval} часов\n\nВыберите новый интервал:"
                
                buttons = [
                    [Button.inline("1 час", b"set_activity_1"), Button.inline("2 часа", b"set_activity_2")],
                    [Button.inline("3 часа", b"set_activity_3"), Button.inline("4 часа", b"set_activity_4")],
                    [Button.inline("🔙 Назад к времени", b"settings_time")]
                ]
                
                await event.edit(message, buttons=buttons)
            else:
                await event.edit("❌ Ошибка получения настроек")
        
        elif data == "set_birth_date":
            baby_birth_pending[uid] = True
            await event.edit("📅 **Установка даты рождения малыша**\n\nВведите дату в формате:\n• **2024-01-15** (15 января 2024)\n• **15.01.2024** (15 января 2024)\n• **15/01/2024** (15 января 2024)")
        
        # Обработка переключения уведомлений
        elif data == "toggle_tips_on":
            fid = get_family_id(uid)
            if fid and update_notification_settings(fid, {"tips_enabled": True}):
                await event.edit("✅ Советы включены!")
            else:
                await event.edit("❌ Ошибка изменения настроек")
        
        elif data == "toggle_tips_off":
            fid = get_family_id(uid)
            if fid and update_notification_settings(fid, {"tips_enabled": False}):
                await event.edit("✅ Советы выключены!")
            else:
                await event.edit("❌ Ошибка изменения настроек")
        
        elif data == "toggle_bath_on":
            fid = get_family_id(uid)
            if fid and update_notification_settings(fid, {"bath_reminder_enabled": True}):
                await event.edit("✅ Напоминания о купании включены!")
            else:
                await event.edit("❌ Ошибка изменения настроек")
        
        elif data == "toggle_bath_off":
            fid = get_family_id(uid)
            if fid and update_notification_settings(fid, {"bath_reminder_enabled": False}):
                await event.edit("✅ Напоминания о купании выключены!")
            else:
                await event.edit("❌ Ошибка изменения настроек")
        
        elif data == "toggle_activity_on":
            fid = get_family_id(uid)
            if fid and update_notification_settings(fid, {"activity_reminder_enabled": True}):
                await event.edit("✅ Напоминания об активности включены!")
            else:
                await event.edit("❌ Ошибка изменения настроек")
        
        elif data == "toggle_activity_off":
            fid = get_family_id(uid)
            if fid and update_notification_settings(fid, {"activity_reminder_enabled": False}):
                await event.edit("✅ Напоминания об активности выключены!")
            else:
                await event.edit("❌ Ошибка изменения настроек")
        
        # Обработка кнопки "Проверить снова" для напоминаний
        elif data == "check_reminders":
            fid = get_family_id(uid)
            if fid:
                # Проверяем условия для напоминаний
                conditions = check_smart_reminder_conditions(fid)
                
                if not conditions['needs_feeding'] and not conditions['needs_diaper']:
                    message = "✅ **Все в порядке!**\n\n"
                    message += "🍼 Кормление и смена подгузника по расписанию\n"
                    message += "💡 Напоминания работают в фоновом режиме"
                    
                    buttons = [
                        [Button.inline("🔄 Проверить снова", b"check_reminders")]
                    ]
                else:
                    # Получаем сообщение напоминания
                    message = get_smart_reminder_message(fid)
                    if not message:
                        message = "❌ Ошибка получения напоминаний"
                        buttons = []
                    else:
                        # Создаем кнопки для быстрых действий
                        buttons = []
                        if conditions['needs_feeding']:
                            buttons.append([Button.inline("🍼 Отметить кормление", b"feed_now")])
                        if conditions['needs_diaper']:
                            buttons.append([Button.inline("💩 Смена подгузника", b"diaper_now")])
                        buttons.append([Button.inline("🔄 Проверить снова", b"check_reminders")])
                
                await event.edit(message, buttons=buttons)
            else:
                await event.edit("❌ Ошибка получения напоминаний")
        
        # Обработка кнопки "Назад к настройкам"
        elif data == "back_to_settings":
            fid = get_family_id(uid)
            if fid:
                # Получаем настройки и статистику
                settings = get_notification_settings(fid)
                intervals = get_user_intervals(fid)
                feeding_stats = get_feeding_stats(fid)
                diaper_stats = get_diaper_stats(fid)
                bath_stats = get_bath_stats(fid)
                activity_stats = get_activity_stats(fid)
                birth_date = get_birth_date(fid)
                
                message = "⚙️ **Настройки и статистика:**\n\n"
                
                # Статистика за сегодня
                message += "📊 **Статистика за сегодня:**\n"
                if feeding_stats:
                    message += f"🍼 Кормления: {feeding_stats['count']} раз\n"
                if diaper_stats:
                    message += f"💩 Смены подгузников: {diaper_stats['count']} раз\n"
                if bath_stats:
                    message += f"🛁 Купания: {bath_stats['count']} раз\n"
                if activity_stats:
                    message += f"🎮 Активность: {activity_stats['count']} раз\n"
                
                message += "\n⚙️ **Текущие настройки:**\n"
                
                if intervals:
                    feed_interval, diaper_interval = intervals
                    message += f"🍼 Интервал кормления: {feed_interval}ч\n"
                    message += f"💩 Интервал смены подгузника: {diaper_interval}ч\n\n"
                
                if settings:
                    message += f"💡 Советы: {'Включены' if settings.get('tips_enabled') else 'Выключены'}\n"
                    message += f"🛁 Напоминания о купании: {'Включены' if settings.get('bath_reminder_enabled') else 'Выключены'}\n"
                    message += f"🎮 Напоминания об активности: {'Включены' if settings.get('activity_reminder_enabled') else 'Выключены'}\n"
                
                if birth_date:
                    message += f"📅 Дата рождения малыша: {birth_date}\n"
                else:
                    message += f"📅 Дата рождения малыша: Не установлена\n"
                
                message += "\n🎯 **Что настроим?**"
                
                buttons = [
                    [Button.inline("🍼 Интервал кормления", b"settings_feeding"), Button.inline("💩 Интервал подгузников", b"settings_diaper")],
                    [Button.inline("💡 Советы", b"settings_tips"), Button.inline("🛁 Купание", b"settings_bath")],
                    [Button.inline("🎮 Активность", b"settings_activity"), Button.inline("⏰ Время уведомлений", b"settings_time")],
                    [Button.inline("📅 Дата рождения", b"settings_birth_date"), Button.inline("🔙 Назад", b"back_to_main")]
                ]
                
                await event.edit(message, buttons=buttons)
            else:
                await event.edit("❌ Ошибка получения настроек")
        
        else:
            await event.answer("❌ Неизвестная команда")
    
    @client.on(events.NewMessage)
    async def handle_text(event):
        uid = event.sender_id
        text = event.text.strip()
        
        # Обработка создания семьи
        if uid in family_creation_pending:
            family_name = text
            family_id = create_family(family_name, uid)
            
            if family_id:
                del family_creation_pending[uid]
                await event.respond(f"✅ Семья '{family_name}' создана! ID семьи: {family_id}")
            else:
                await event.respond("❌ Ошибка создания семьи")
            return
        
        # Обработка присоединения к семье
        if uid in join_pending:
            family_id, family_name = join_family_by_code(text, uid)
            
            if family_id:
                del join_pending[uid]
                await event.respond(f"✅ Вы присоединились к семье '{family_name}'!")
            else:
                await event.respond(f"❌ {family_name}")
            return
        
        # Обработка ввода времени
        if uid in custom_time_pending:
            action = custom_time_pending[uid]
            del custom_time_pending[uid]
            
            if action in ["feeding", "diaper"]:
                minutes_ago = parse_time_input(text)
                if minutes_ago is None:
                    await event.respond("❌ Неверный формат времени. Попробуйте снова.")
                    return
                
                if action == "feeding":
                    success, message = handle_feeding_callback(event, minutes_ago)
                    if success:
                        await event.respond(message)
                    else:
                        if isinstance(message, tuple):
                            await event.respond(message[0], buttons=message[1])
                        else:
                            await event.respond(message)
                elif action == "diaper":
                    success, message = handle_diaper_callback(event, minutes_ago)
                    if success:
                        await event.respond(message)
                    else:
                        if isinstance(message, tuple):
                            await event.respond(message[0], buttons=message[1])
                        else:
                            await event.respond(message)
            
            elif action in ["tips_time", "bath_time"]:
                # Парсим время для настроек
                time_tuple = parse_time_setting(text)
                if time_tuple is None:
                    await event.respond("❌ Неверный формат времени. Попробуйте снова.")
                    return
                
                hours, minutes = time_tuple
                fid = get_family_id(uid)
                
                if action == "tips_time":
                    if fid and update_notification_settings(fid, {"tips_time_hour": hours, "tips_time_minute": minutes}):
                        await event.respond(f"✅ Время советов изменено на {hours:02d}:{minutes:02d}!")
                    else:
                        await event.respond("❌ Ошибка изменения времени")
                elif action == "bath_time":
                    if fid and update_notification_settings(fid, {"bath_reminder_hour": hours, "bath_reminder_minute": minutes}):
                        await event.respond(f"✅ Время купания изменено на {hours:02d}:{minutes:02d}!")
                    else:
                        await event.respond("❌ Ошибка изменения времени")
            return
        
        # Обработка ввода даты рождения
        if uid in baby_birth_pending:
            del baby_birth_pending[uid]
            
            # Парсим дату рождения
            birth_date = parse_birth_date(text)
            if birth_date is None:
                await event.respond("❌ Неверный формат даты. Попробуйте снова.\n\nИспользуйте формат:\n• **2024-01-15**\n• **15.01.2024**\n• **15/01/2024**")
                return
            
            fid = get_family_id(uid)
            if fid and set_birth_date(fid, birth_date):
                await event.respond(f"✅ Дата рождения установлена: {birth_date}")
            else:
                await event.respond("❌ Ошибка установки даты рождения")
            return
        
        if text == "👨‍👩‍👧 Создать семью":
            family_creation_pending[uid] = True
            await event.respond("👨‍👩‍👧 Введите название новой семьи:")
        
        elif text == "🔗 Присоединиться":
            join_pending[uid] = True
            await event.respond("🔗 Введите код семьи (ID семьи):")
        
        elif text == "💡 Совет":
            fid = get_family_id(uid)
            if fid:
                age_months = get_baby_age_months(fid)
                tip = get_random_tip(age_months)
                if tip:
                    await event.respond(f"💡 **Совет для {age_months} месяцев:**\n\n{tip}")
                else:
                    await event.respond("💡 Советов для вашего возраста пока нет")
            else:
                await event.respond("❌ Вы не состоите в семье")
        
        elif text == "⚙ Настройки":
            fid = get_family_id(uid)
            if fid:
                message = "⚙️ **Настройки**\n\n🎯 **Что настроим?**"
                buttons = [
                    [Button.text("🍼 Интервалы кормления"), Button.text("🧷 Интервалы подгузников")],
                    [Button.text("👤 Моя роль"), Button.text("📅 Дата рождения")],
                    [Button.text("🔙 Назад")]
                ]
                await event.respond(message, buttons=buttons)
            else:
                await event.respond("❌ Вы не состоите в семье")
        
        
        elif text == "👨‍👩‍👧 Семья":
            fid = get_family_id(uid)
            if fid:
                family_name = get_family_name(fid)
                members = get_family_members_with_roles(fid)
                
                message = f"👨‍👩‍👧 **Семья: {family_name}**\n\n"
                message += f"👥 **Члены семьи:**\n"
                
                for user_id, role, name in members:
                    if user_id == uid:
                        message += f"• {role} {name} (вы)\n"
                    else:
                        message += f"• {role} {name}\n"
                
                message += f"\n🔑 **ID семьи:** {fid}\n"
                message += f"Поделитесь этим ID с другими членами семьи"
                
                buttons = [[Button.text("🔙 Назад")]]
                await event.respond(message, buttons=buttons)
            else:
                await event.respond("❌ Вы не состоите в семье")
        
        
    
    # Запускаем бота с обработкой очереди напоминаний
    try:
        print("🔄 Запускаем обработчик напоминаний...")
        # Создаем задачу для обработки очереди напоминаний
        async def reminder_processor():
            while True:
                await process_reminder_queue()
                await asyncio.sleep(10)  # Проверяем каждые 10 секунд
        
        # Запускаем обработчик напоминаний в фоне
        asyncio.create_task(reminder_processor())
        print("✅ Обработчик напоминаний запущен")
        
        print("🔄 Запускаем основной цикл бота...")
        await client.run_until_disconnected()
    except KeyboardInterrupt:
        print("\n🛑 Получен сигнал остановки...")
    except Exception as e:
        print(f"❌ Ошибка в работе бота: {e}")
    finally:
        # Graceful shutdown
        print("🔄 Остановка планировщика...")
        scheduler.shutdown()
        print("✅ Планировщик остановлен")
        print("👋 BabyCareBot остановлен")

if __name__ == "__main__":
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
