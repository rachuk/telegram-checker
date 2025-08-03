#!/usr/bin/env python3
"""
Простая система уведомлений в Telegram для мониторинга системы
"""

import requests
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.last_notification_time = {}
        self.notification_cooldown = 300  # 5 минут между уведомлениями
        
    def send_message(self, message: str, alert_type: str = "general") -> bool:
        """Отправляет сообщение в Telegram"""
        # Проверяем cooldown
        current_time = time.time()
        last_time = self.last_notification_time.get(alert_type, 0)
        
        if current_time - last_time < self.notification_cooldown:
            logger.info(f"Уведомление {alert_type} пропущено (cooldown)")
            return False
            
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                self.last_notification_time[alert_type] = current_time
                logger.info(f"Telegram уведомление отправлено: {alert_type}")
                return True
            else:
                logger.error(f"Ошибка отправки Telegram: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка Telegram уведомления: {e}")
            return False
    
    def send_critical_alert(self, message: str) -> bool:
        """Отправляет критическое уведомление"""
        formatted_message = f"🚨 <b>КРИТИЧЕСКАЯ ОШИБКА</b>\n\n{message}\n\n⏰ {time.strftime('%Y-%m-%d %H:%M:%S')}"
        return self.send_message(formatted_message, "critical")
    
    def send_warning_alert(self, message: str) -> bool:
        """Отправляет предупреждение"""
        formatted_message = f"⚠️ <b>ПРЕДУПРЕЖДЕНИЕ</b>\n\n{message}\n\n⏰ {time.strftime('%Y-%m-%d %H:%M:%S')}"
        return self.send_message(formatted_message, "warning")
    
    def send_info_alert(self, message: str) -> bool:
        """Отправляет информационное сообщение"""
        formatted_message = f"ℹ️ <b>ИНФОРМАЦИЯ</b>\n\n{message}\n\n⏰ {time.strftime('%Y-%m-%d %H:%M:%S')}"
        return self.send_message(formatted_message, "info")
    
    def send_success_alert(self, message: str) -> bool:
        """Отправляет сообщение об успехе"""
        formatted_message = f"✅ <b>УСПЕХ</b>\n\n{message}\n\n⏰ {time.strftime('%Y-%m-%d %H:%M:%S')}"
        return self.send_message(formatted_message, "success")

# Глобальный экземпляр уведомлений
notifier = TelegramNotifier(
    bot_token="8249088814:AAHhMajR1obd91FNJ4Hxt0Bbgm1YFwaBDdQ",
    chat_id="229956339"
)

# Переменные для периодических отчетов
last_report_time = 0
report_interval = 4 * 3600  # 4 часа в секундах

def check_system_status(health_data: dict) -> None:
    """Проверяет статус системы и отправляет уведомления при проблемах"""
    global last_report_time
    
    if not health_data:
        notifier.send_critical_alert("❌ Не удается получить данные о состоянии системы")
        return
    
    # Проверяем доступность аккаунтов
    available_accounts = 0
    total_enabled = 0
    flood_wait_accounts = []
    error_accounts = []
    
    for account_name, account_data in health_data.get("accounts", {}).items():
        if account_data.get("enabled"):
            total_enabled += 1
            
            if account_data.get("ready") and account_data.get("flood_wait_until", 0) <= 0:
                available_accounts += 1
            elif account_data.get("flood_wait_until", 0) > 0:
                flood_wait_accounts.append(account_name)
            
            if account_data.get("errors_count", 0) > 5:
                error_accounts.append(f"{account_name} ({account_data['errors_count']} ошибок)")
    
    # Критическое уведомление: нет доступных аккаунтов
    if available_accounts == 0 and total_enabled > 0:
        message = f"🚨 <b>НЕТ ДОСТУПНЫХ АККАУНТОВ!</b>\n\n"
        message += f"📊 Всего включенных: {total_enabled}\n"
        message += f"✅ Доступных: {available_accounts}\n"
        message += f"⏳ В FloodWait: {len(flood_wait_accounts)}\n"
        if flood_wait_accounts:
            message += f"🔴 Заблокированные: {', '.join(flood_wait_accounts)}\n"
        if error_accounts:
            message += f"⚠️ Проблемные: {', '.join(error_accounts)}"
        
        notifier.send_critical_alert(message)
    
    # Предупреждение: много аккаунтов в FloodWait
    elif flood_wait_accounts and len(flood_wait_accounts) >= 2:
        message = f"⚠️ <b>МНОГО АККАУНТОВ В FLOODWAIT</b>\n\n"
        message += f"🔴 Заблокированные: {', '.join(flood_wait_accounts)}\n"
        message += f"✅ Доступных: {available_accounts}/{total_enabled}"
        
        notifier.send_warning_alert(message)
    
    # Предупреждение: высокое количество ошибок
    elif error_accounts:
        message = f"⚠️ <b>ВЫСОКОЕ КОЛИЧЕСТВО ОШИБОК</b>\n\n"
        message += f"Проблемные аккаунты:\n{chr(10).join(error_accounts)}"
        
        notifier.send_warning_alert(message)
    
    # Информация: система восстановлена
    elif available_accounts > 0 and available_accounts == total_enabled:
        message = f"✅ <b>СИСТЕМА ВОССТАНОВЛЕНА</b>\n\n"
        message += f"Все {available_accounts} аккаунтов готовы к работе"
        
        notifier.send_success_alert(message)
    
    # Периодический отчет каждые 4 часа
    current_time = time.time()
    if current_time - last_report_time >= report_interval:
        send_periodic_report(health_data)
        last_report_time = current_time

def send_periodic_report(health_data: dict) -> None:
    """Отправляет периодический отчет о состоянии системы"""
    if not health_data:
        return
    
    accounts = health_data.get("accounts", {})
    
    # Подсчитываем статистику
    total_enabled = 0
    available_accounts = 0
    flood_wait_accounts = 0
    total_requests = 0
    total_errors = 0
    account_details = []
    
    for account_name, account_data in accounts.items():
        if account_data.get("enabled"):
            total_enabled += 1
            requests_count = account_data.get("current_requests", 0)
            errors_count = account_data.get("errors_count", 0)
            total_requests += requests_count
            total_errors += errors_count
            
            if account_data.get("ready") and account_data.get("flood_wait_until", 0) <= 0:
                available_accounts += 1
                status = "✅"
            elif account_data.get("flood_wait_until", 0) > 0:
                flood_wait_accounts += 1
                status = "🔴"
            else:
                status = "⚠️"
            
            # Добавляем детали аккаунта
            max_requests = account_data.get("max_requests_per_hour", 0)
            usage_percent = (requests_count / max_requests * 100) if max_requests > 0 else 0
            account_details.append(f"{status} {account_name}: {requests_count}/{max_requests} ({usage_percent:.1f}%) | {errors_count} ошибок")
    
    # Формируем отчет
    message = f"📊 <b>ПЕРИОДИЧЕСКИЙ ОТЧЕТ (4 часа)</b>\n\n"
    message += f"🕐 Время: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    message += f"📱 Всего аккаунтов: {total_enabled}\n"
    message += f"✅ Доступных: {available_accounts}\n"
    message += f"🔴 В FloodWait: {flood_wait_accounts}\n"
    message += f"📈 Всего запросов: {total_requests}\n"
    message += f"❌ Всего ошибок: {total_errors}\n\n"
    
    if account_details:
        message += "<b>Детали по аккаунтам:</b>\n"
        message += "\n".join(account_details)
    
    # Определяем общий статус
    if available_accounts == 0:
        message += "\n\n🚨 <b>КРИТИЧЕСКОЕ СОСТОЯНИЕ</b>"
    elif available_accounts < total_enabled * 0.5:
        message += "\n\n⚠️ <b>ВНИМАНИЕ</b> - мало доступных аккаунтов"
    else:
        message += "\n\n✅ <b>СТАБИЛЬНАЯ РАБОТА</b>"
    
    notifier.send_info_alert(message)

def force_send_report():
    """Принудительно отправляет отчет о текущем состоянии"""
    try:
        import requests
        response = requests.get("http://localhost:5000/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            send_periodic_report(health_data)
            print("✅ Отчет отправлен!")
        else:
            print("❌ Не удалось получить данные о системе")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def test_notifications():
    """Тестирует все типы уведомлений"""
    print("🧪 Тестирование уведомлений...")
    
    notifier.send_info_alert("Тестовое информационное сообщение")
    time.sleep(1)
    
    notifier.send_warning_alert("Тестовое предупреждение")
    time.sleep(1)
    
    notifier.send_critical_alert("Тестовое критическое уведомление")
    time.sleep(1)
    
    notifier.send_success_alert("Тестовое сообщение об успехе")
    
    print("✅ Тестовые уведомления отправлены!")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        force_send_report()
    else:
        test_notifications() 