from pathlib import Path
import re

path = Path('supabase_client.py')
text = path.read_text(encoding='utf-8')

pattern_pre = r"def check_pre_reminder_conditions\(family_id: int\) -> Dict\[str, Any\]:\n(?:    .*\n|\n)+?(?=def check_overdue_reminder_conditions)"
new_pre = """def check_pre_reminder_conditions(family_id: int) -> Dict[str, Any]:\n    \"\"\"Check if a pre-reminder should be sent five minutes before the event.\"\"\"\n    try:\n        settings = get_notification_settings(family_id)\n        if not settings:\n            return {'needs_pre_feeding': False, 'needs_pre_diaper': False}\n\n        time_until_feeding = get_time_until_next_feeding(family_id)\n        minutes_until_feeding = None\n        needs_pre_feeding = False\n\n        if time_until_feeding is not None:\n            minutes_until_feeding = time_until_feeding * 60\n            needs_pre_feeding = 0 < minutes_until_feeding <= 5\n\n        time_until_diaper = get_time_until_next_diaper_change(family_id)\n        minutes_until_diaper = None\n        needs_pre_diaper = False\n\n        if time_until_diaper is not None:\n            minutes_until_diaper = time_until_diaper * 60\n            needs_pre_diaper = 0 < minutes_until_diaper <= 5\n\n        return {\n            'needs_pre_feeding': needs_pre_feeding,\n            'needs_pre_diaper': needs_pre_diaper,\n            'time_until_feeding': time_until_feeding,\n            'time_until_diaper': time_until_diaper,\n            'minutes_until_feeding': minutes_until_feeding,\n            'minutes_until_diaper': minutes_until_diaper\n        }\n    except Exception as e:\n        print(f\"[Notifications] Failed to evaluate pre-reminder conditions: {e}\")\n        return {'needs_pre_feeding': False, 'needs_pre_diaper': False}\n\n"""
text, count = re.subn(pattern_pre, new_pre, text, flags=re.DOTALL)
if count != 1:
    raise RuntimeError('Failed to update check_pre_reminder_conditions')

pattern_overdue = r"def check_overdue_reminder_conditions\(family_id: int\) -> Dict\[str, Any\]:\n(?:    .*\n|\n)+?(?=def get_pre_reminder_message)"
new_overdue = """def check_overdue_reminder_conditions(family_id: int) -> Dict[str, Any]:\n    \"\"\"Check if an overdue reminder should be sent 25 minutes after the due time.\"\"\"\n    try:\n        settings = get_notification_settings(family_id)\n        if not settings:\n            return {'needs_overdue_feeding': False, 'needs_overdue_diaper': False}\n\n        feed_interval = settings.get('feed_interval', 3)\n        diaper_interval = settings.get('diaper_interval', 2)\n\n        last_feeding = get_last_feeding_time_for_family(family_id)\n        needs_overdue_feeding = False\n        hours_since_feeding = 0\n        minutes_overdue_feeding = 0\n\n        if last_feeding:\n            now = get_thai_time()\n            time_diff = now - last_feeding\n            hours_since_feeding = time_diff.total_seconds() / 3600\n            minutes_overdue_feeding = max(0, (hours_since_feeding - feed_interval) * 60)\n            needs_overdue_feeding = minutes_overdue_feeding >= 25\n\n        last_diaper = get_last_diaper_change_time_for_family(family_id)\n        needs_overdue_diaper = False\n        hours_since_diaper = 0\n        minutes_overdue_diaper = 0\n\n        if last_diaper:\n            now = get_thai_time()\n            time_diff = now - last_diaper\n            hours_since_diaper = time_diff.total_seconds() / 3600\n            minutes_overdue_diaper = max(0, (hours_since_diaper - diaper_interval) * 60)\n            needs_overdue_diaper = minutes_overdue_diaper >= 25\n\n        return {\n            'needs_overdue_feeding': needs_overdue_feeding,\n            'needs_overdue_diaper': needs_overdue_diaper,\n            'hours_since_feeding': hours_since_feeding if last_feeding else 0,\n            'hours_since_diaper': hours_since_diaper if last_diaper else 0,\n            'minutes_overdue_feeding': minutes_overdue_feeding,\n            'minutes_overdue_diaper': minutes_overdue_diaper\n        }\n    except Exception as e:\n        print(f\"[Notifications] Failed to evaluate overdue reminder conditions: {e}\")\n        return {'needs_overdue_feeding': False, 'needs_overdue_diaper': False}\n\n"""
text, count = re.subn(pattern_overdue, new_overdue, text, flags=re.DOTALL)
if count != 1:
    raise RuntimeError('Failed to update check_overdue_reminder_conditions')

text = text.replace(
    "        if conditions['needs_pre_feeding']:\n            time_until = conditions['time_until_feeding']\n            if time_until is not None:\n                minutes_left = int(time_until * 60)\n                if minutes_left > 0:\n                    message += f\"🍼 **Напоминание о кормлении**\\n\\n🚨 **Запланировано через {minutes_left} минут**\\n\"\n",
    "        if conditions['needs_pre_feeding']:\n            minutes_left = conditions.get('minutes_until_feeding')\n            if minutes_left is not None:\n                display_minutes = max(1, int(round(minutes_left)))\n                if minutes_left > 0:\n                    message += f\"🍼 **Напоминание о кормлении**\\n\\n🚨 **Запланировано через {display_minutes} минут**\\n\"\n"
)

text = text.replace(
    "        if conditions['needs_pre_diaper']:\n            time_until = conditions['time_until_diaper']\n            if time_until is not None:\n                minutes_left = int(time_until * 60)\n                if minutes_left > 0:\n                    message += f\"💩 **Напоминание о смене подгузника**\\n\\n🚨 **Запланировано через {minutes_left} минут**\\n\"\n",
    "        if conditions['needs_pre_diaper']:\n            minutes_left = conditions.get('minutes_until_diaper')\n            if minutes_left is not None:\n                display_minutes = max(1, int(round(minutes_left)))\n                if minutes_left > 0:\n                    message += f\"💩 **Напоминание о смене подгузника**\\n\\n🚨 **Запланировано через {display_minutes} минут**\\n\"\n"
)

text = text.replace("15+", "25+")

text = re.sub(r"def create_notification_tracking_table\(\):\n(?:    .*\n|\n)+?(?=def log_notification_sent)", "", text, flags=re.DOTALL)
text = re.sub(r"def clear_family_cache\(user_id: int = None\):\n(?:    .*\n|\n)+?(?=def get_cache_stats|def init_supabase)", "", text, flags=re.DOTALL)
text = re.sub(r"def get_cache_stats\(\):\n(?:    .*\n|\n)+?(?=def init_supabase)", "", text, flags=re.DOTALL)

path.write_text(text, encoding='utf-8')
