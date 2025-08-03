#!/usr/bin/env python3
"""
Скрипт для мониторинга системы с уведомлениями в Telegram
"""

import requests
import time
import json
from telegram_notifications import notifier, check_system_status

def get_system_health():
    """Получает данные о состоянии системы"""
    try:
        response = requests.get("http://localhost:5000/health", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        print(f"Ошибка получения данных: {e}")
        return None

def monitor_system():
    """Мониторит систему и отправляет уведомления"""
    print("🔍 Запуск мониторинга системы...")
    print("📱 Уведомления будут отправляться в Telegram")
    print("⏰ Проверка каждые 30 секунд")
    print("=" * 50)
    
    last_status = None
    
    while True:
        try:
            health_data = get_system_health()
            
            if not health_data:
                print(f"❌ {time.strftime('%H:%M:%S')} - Не удается получить данные о системе")
                notifier.send_critical_alert("❌ Сервис недоступен - не удается получить данные")
                time.sleep(30)
                continue
            
            # Проверяем статус системы
            check_system_status(health_data)
            
            # Выводим текущий статус
            ready_clients = health_data.get("ready_clients", 0)
            enabled_accounts = health_data.get("enabled_accounts", 0)
            available_accounts = sum(1 for acc in health_data.get("accounts", {}).values() 
                                   if acc.get("enabled") and acc.get("ready") and acc.get("flood_wait_until", 0) <= 0)
            
            current_status = f"✅ {ready_clients}/{enabled_accounts} аккаунтов готово, {available_accounts} доступно"
            
            if current_status != last_status:
                print(f"📊 {time.strftime('%H:%M:%S')} - {current_status}")
                last_status = current_status
            
            time.sleep(30)
            
        except KeyboardInterrupt:
            print("\n🛑 Мониторинг остановлен")
            break
        except Exception as e:
            print(f"❌ Ошибка мониторинга: {e}")
            time.sleep(30)

if __name__ == "__main__":
    monitor_system() 