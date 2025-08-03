#!/usr/bin/env python3
"""
Быстрый старт для настройки множественных Telegram аккаунтов
"""

import os
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich import print as rprint

console = Console()

def check_dependencies():
    """Проверяет наличие необходимых зависимостей"""
    try:
        import telethon
        import flask
        import requests
        import rich
        rprint("✅ Все зависимости установлены")
        return True
    except ImportError as e:
        rprint(f"❌ Отсутствует зависимость: {e}")
        rprint("Установите: pip install -r requirements.txt")
        return False

def create_sample_config():
    """Создает пример конфигурации"""
    config_content = {
        "accounts": [
            {
                "name": "account1",
                "api_id": "YOUR_API_ID_1",
                "api_hash": "YOUR_API_HASH_1",
                "phone": "+1234567890",
                "session_file": "session_account1.session",
                "enabled": True,
                "max_requests_per_hour": 50
            },
            {
                "name": "account2", 
                "api_id": "YOUR_API_ID_2",
                "api_hash": "YOUR_API_HASH_2",
                "phone": "+0987654321",
                "session_file": "session_account2.session",
                "enabled": True,
                "max_requests_per_hour": 50
            }
        ]
    }
    
    import json
    with open("multi_account_config.json", "w", encoding="utf-8") as f:
        json.dump(config_content, f, indent=2, ensure_ascii=False)
    
    rprint("📝 Создан пример конфигурации: multi_account_config.json")
    rprint("   Отредактируйте файл с вашими данными")

def create_sample_contacts():
    """Создает пример файла с контактами"""
    sample_contacts = [
        "+1234567890",
        "+9876543210", 
        "username1",
        "username2"
    ]
    
    # Создаем разные форматы
    with open("sample_contacts.txt", "w", encoding="utf-8") as f:
        for contact in sample_contacts:
            f.write(f"{contact}\n")
    
    import csv
    with open("sample_contacts.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for contact in sample_contacts:
            writer.writerow([contact])
    
    rprint("📝 Созданы примеры файлов с контактами:")
    rprint("   - sample_contacts.txt")
    rprint("   - sample_contacts.csv")

def show_instructions():
    """Показывает инструкции по настройке"""
    rprint(Panel.fit("📋 Пошаговая инструкция", style="bold blue"))
    
    rprint("""
1️⃣ Подготовка аккаунтов:
   • Создайте несколько Telegram аккаунтов
   • Получите API ID и Hash на https://my.telegram.org/apps
   • Для каждого аккаунта нужны: API ID, API Hash, номер телефона

2️⃣ Настройка системы:
   • Запустите: python setup_multi_accounts.py
   • Добавьте каждый аккаунт
   • Протестируйте подключение
   • Сохраните конфигурацию

3️⃣ Запуск API:
   • Запустите: python flask_api_multi.py
   • Или через systemd: sudo systemctl start telegram-checker-multi

4️⃣ Массовая проверка:
   • Подготовьте файл с контактами (TXT/CSV/JSON)
   • Запустите: python bulk_checker.py
   • Выберите файл и настройки

5️⃣ Мониторинг:
   • Проверка здоровья: curl http://localhost:5000/health
   • Статус аккаунтов: curl http://localhost:5000/accounts/status
   • Логи: tail -f telegram_checker_multi.log
    """)

def main():
    rprint(Panel.fit("🚀 Быстрый старт - Множественные Telegram аккаунты", style="bold green"))
    
    # Проверяем зависимости
    if not check_dependencies():
        return
    
    rprint("\n" + "="*60)
    rprint("Выберите действие:")
    rprint("1. Создать пример конфигурации")
    rprint("2. Создать пример файлов с контактами") 
    rprint("3. Показать инструкции")
    rprint("4. Запустить настройку аккаунтов")
    rprint("5. Запустить API")
    rprint("6. Запустить массовую проверку")
    rprint("0. Выход")
    
    choice = input("\nВведите номер: ").strip()
    
    if choice == "1":
        create_sample_config()
        rprint("\n📝 Теперь отредактируйте multi_account_config.json с вашими данными")
        
    elif choice == "2":
        create_sample_contacts()
        rprint("\n📝 Файлы созданы. Замените примеры на ваши контакты")
        
    elif choice == "3":
        show_instructions()
        
    elif choice == "4":
        rprint("\n🔧 Запуск настройки аккаунтов...")
        os.system("python setup_multi_accounts.py")
        
    elif choice == "5":
        rprint("\n🚀 Запуск API с множественными аккаунтами...")
        rprint("   API будет доступен на http://localhost:5000")
        rprint("   Для остановки нажмите Ctrl+C")
        os.system("python flask_api_multi.py")
        
    elif choice == "6":
        rprint("\n📊 Запуск массовой проверки...")
        os.system("python bulk_checker.py")
        
    elif choice == "0":
        rprint("👋 До свидания!")
        
    else:
        rprint("❌ Неверный выбор")

if __name__ == "__main__":
    main() 