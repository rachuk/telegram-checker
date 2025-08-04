#!/usr/bin/env python3
"""
Скрипт для принудительной проверки всех аккаунтов и отправки уведомлений
"""

import requests
import json
import time
from datetime import datetime

def check_system_status():
    """Проверяет статус системы и отправляет уведомления"""
    
    try:
        # Получаем статус мониторинга
        response = requests.get('http://localhost:5000/monitoring/status', timeout=10)
        if response.status_code != 200:
            print(f"❌ Ошибка получения статуса: {response.status_code}")
            return
        
        monitoring_data = response.json()
        
        # Получаем детальный статус
        response = requests.post('http://localhost:5000/monitoring/check', timeout=10)
        if response.status_code != 200:
            print(f"❌ Ошибка проверки мониторинга: {response.status_code}")
            return
        
        status_data = response.json()
        
        print("📊 Статус системы:")
        print(f"   Уведомления: {'✅ Включены' if monitoring_data['notifications_enabled'] else '❌ Отключены'}")
        print(f"   Всего аккаунтов: {monitoring_data['total_enabled_accounts']}")
        print(f"   Доступных: {monitoring_data['available_accounts']}")
        print(f"   В FloodWait: {len(monitoring_data['flood_wait_accounts'])}")
        print(f"   Статус: {monitoring_data['system_status']}")
        
        # Анализируем аккаунты
        accounts = status_data['data']['accounts']
        problem_accounts = []
        flood_wait_accounts = []
        ready_accounts = []
        
        for account_name, account_data in accounts.items():
            if not account_data.get('enabled'):
                continue
                
            # Проверяем, истекло ли время FloodWait
            flood_wait_until = account_data.get('flood_wait_until', 0)
            current_time = time.time()
            
            if account_data.get('ready') and flood_wait_until <= current_time:
                ready_accounts.append(account_name)
            elif flood_wait_until > current_time:
                flood_wait_accounts.append(account_name)
            else:
                problem_accounts.append(account_name)
        
        print(f"\n📱 Детали по аккаунтам:")
        print(f"   ✅ Готовы: {', '.join(ready_accounts) if ready_accounts else 'Нет'}")
        print(f"   🔴 FloodWait: {', '.join(flood_wait_accounts) if flood_wait_accounts else 'Нет'}")
        print(f"   ⚠️ Проблемы: {', '.join(problem_accounts) if problem_accounts else 'Нет'}")
        
        # Отправляем уведомление если есть проблемы
        if monitoring_data['system_status'] == 'critical':
            print("\n🚨 КРИТИЧЕСКАЯ СИТУАЦИЯ: Нет доступных аккаунтов!")
        elif monitoring_data['system_status'] == 'warning':
            print(f"\n⚠️ ПРЕДУПРЕЖДЕНИЕ: {len(flood_wait_accounts)} аккаунтов в FloodWait")
        else:
            print(f"\n✅ Система работает нормально")
            
    except Exception as e:
        print(f"❌ Ошибка проверки системы: {e}")

def force_notification():
    """Принудительно отправляет уведомление о статусе"""
    try:
        response = requests.post('http://localhost:5000/monitoring/check', timeout=10)
        if response.status_code == 200:
            print("✅ Уведомление отправлено")
        else:
            print(f"❌ Ошибка отправки уведомления: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == '__main__':
    print("🔍 Проверка системы Telegram Checker")
    print("=" * 50)
    
    check_system_status()
    
    print("\n" + "=" * 50)
    print("Отправка принудительного уведомления...")
    force_notification() 