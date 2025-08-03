#!/usr/bin/env python3
"""
Скрипт для настройки множественных Telegram аккаунтов
"""

import json
import os
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich import print as rprint
from rich.table import Table
from rich.panel import Panel

from multi_account_manager import MultiAccountManager, AccountConfig

console = Console()

def create_account_config():
    """Создает конфигурацию для нового аккаунта"""
    rprint(Panel.fit("🔧 Настройка нового Telegram аккаунта", style="bold blue"))
    
    name = Prompt.ask("Введите название аккаунта", default="account1")
    api_id = Prompt.ask("Введите API ID (получите на https://my.telegram.org/apps)")
    api_hash = Prompt.ask("Введите API Hash")
    phone = Prompt.ask("Введите номер телефона с кодом страны", default="+7")
    
    session_file = f"session_{name}.session"
    
    return AccountConfig(
        name=name,
        api_id=api_id,
        api_hash=api_hash,
        phone=phone,
        session_file=session_file,
        enabled=True,
        max_requests_per_hour=50
    )

def test_account(account: AccountConfig):
    """Тестирует подключение аккаунта"""
    rprint(f"\n🧪 Тестирование аккаунта {account.name}...")
    
    try:
        from telethon.sync import TelegramClient
        
        client = TelegramClient(
            account.session_file,
            int(account.api_id),
            account.api_hash
        )
        
        with client:
            if client.is_user_authorized():
                me = client.get_me()
                rprint(f"✅ Аккаунт {account.name} работает! Пользователь: @{me.username or 'без username'}")
                return True
            else:
                rprint(f"❌ Аккаунт {account.name} не авторизован")
                return False
                
    except Exception as e:
        rprint(f"❌ Ошибка тестирования аккаунта {account.name}: {e}")
        return False

def main():
    rprint(Panel.fit("🚀 Настройка множественных Telegram аккаунтов", style="bold green"))
    
    manager = MultiAccountManager()
    
    while True:
        rprint("\n" + "="*50)
        rprint("📋 Доступные действия:")
        rprint("1. Добавить новый аккаунт")
        rprint("2. Просмотреть существующие аккаунты")
        rprint("3. Тестировать все аккаунты")
        rprint("4. Удалить аккаунт")
        rprint("5. Редактировать аккаунт")
        rprint("6. Сохранить и выйти")
        rprint("0. Выход без сохранения")
        
        choice = Prompt.ask("Выберите действие", choices=["0", "1", "2", "3", "4", "5", "6"])
        
        if choice == "0":
            if Confirm.ask("Выйти без сохранения?"):
                break
        
        elif choice == "1":
            account = create_account_config()
            
            if Confirm.ask(f"Добавить аккаунт '{account.name}'?"):
                manager.accounts[account.name] = account
                rprint(f"✅ Аккаунт {account.name} добавлен")
                
                if Confirm.ask("Протестировать аккаунт сейчас?"):
                    test_account(account)
        
        elif choice == "2":
            if not manager.accounts:
                rprint("📭 Нет настроенных аккаунтов")
                continue
            
            table = Table(title="📱 Настроенные аккаунты")
            table.add_column("Название", style="cyan")
            table.add_column("Телефон", style="green")
            table.add_column("Статус", style="yellow")
            table.add_column("Лимит/час", style="blue")
            
            for name, account in manager.accounts.items():
                status = "✅ Включен" if account.enabled else "❌ Отключен"
                table.add_row(
                    name,
                    account.phone,
                    status,
                    str(account.max_requests_per_hour)
                )
            
            console.print(table)
        
        elif choice == "3":
            if not manager.accounts:
                rprint("📭 Нет настроенных аккаунтов")
                continue
            
            rprint("\n🧪 Тестирование всех аккаунтов...")
            working_accounts = 0
            
            for name, account in manager.accounts.items():
                if test_account(account):
                    working_accounts += 1
            
            rprint(f"\n📊 Результат: {working_accounts}/{len(manager.accounts)} аккаунтов работают")
        
        elif choice == "4":
            if not manager.accounts:
                rprint("📭 Нет настроенных аккаунтов")
                continue
            
            account_names = list(manager.accounts.keys())
            rprint("\n🗑️ Выберите аккаунт для удаления:")
            for i, name in enumerate(account_names, 1):
                rprint(f"{i}. {name}")
            
            try:
                idx = int(Prompt.ask("Введите номер")) - 1
                if 0 <= idx < len(account_names):
                    name = account_names[idx]
                    if Confirm.ask(f"Удалить аккаунт '{name}'?"):
                        del manager.accounts[name]
                        rprint(f"✅ Аккаунт {name} удален")
                else:
                    rprint("❌ Неверный номер")
            except ValueError:
                rprint("❌ Неверный ввод")
        
        elif choice == "5":
            if not manager.accounts:
                rprint("📭 Нет настроенных аккаунтов")
                continue
            
            account_names = list(manager.accounts.keys())
            rprint("\n✏️ Выберите аккаунт для редактирования:")
            for i, name in enumerate(account_names, 1):
                rprint(f"{i}. {name}")
            
            try:
                idx = int(Prompt.ask("Введите номер")) - 1
                if 0 <= idx < len(account_names):
                    name = account_names[idx]
                    account = manager.accounts[name]
                    
                    rprint(f"\n✏️ Редактирование аккаунта '{name}':")
                    rprint(f"Текущий лимит: {account.max_requests_per_hour} запросов/час")
                    
                    new_limit = Prompt.ask("Новый лимит запросов в час", default=str(account.max_requests_per_hour))
                    try:
                        account.max_requests_per_hour = int(new_limit)
                        rprint(f"✅ Лимит обновлен: {account.max_requests_per_hour}")
                    except ValueError:
                        rprint("❌ Неверное значение")
                        
                    if Confirm.ask("Включить/отключить аккаунт?"):
                        account.enabled = not account.enabled
                        status = "включен" if account.enabled else "отключен"
                        rprint(f"✅ Аккаунт {status}")
                else:
                    rprint("❌ Неверный номер")
            except ValueError:
                rprint("❌ Неверный ввод")
        
        elif choice == "6":
            manager.save_config()
            rprint("✅ Конфигурация сохранена!")
            break
    
    rprint("\n🎉 Настройка завершена!")
    rprint("Теперь запустите: python flask_api_multi.py")

if __name__ == "__main__":
    main() 