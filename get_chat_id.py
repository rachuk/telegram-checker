#!/usr/bin/env python3
"""
Скрипт для получения chat_id от Telegram бота
"""

import requests
import time

BOT_TOKEN = "8249088814:AAHhMajR1obd91FNJ4Hxt0Bbgm1YFwaBDdQ"

def get_updates():
    """Получает обновления от бота"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                return data.get("result", [])
        return []
    except Exception as e:
        print(f"Ошибка при получении обновлений: {e}")
        return []

def send_test_message(chat_id):
    """Отправляет тестовое сообщение"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "🤖 Тестовое сообщение от Telegram Checker!\n\nСистема уведомлений работает!"
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print(f"✅ Тестовое сообщение отправлено в чат {chat_id}")
            return True
        else:
            print(f"❌ Ошибка отправки: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def main():
    print("🤖 Telegram Bot Chat ID Finder")
    print("=" * 40)
    print(f"Токен бота: {BOT_TOKEN}")
    print()
    print("📱 Инструкция:")
    print("1. Найдите вашего бота в Telegram")
    print("2. Отправьте ему команду /start")
    print("3. Нажмите Enter здесь для проверки")
    print()
    
    input("Нажмите Enter после отправки /start боту...")
    
    updates = get_updates()
    
    if not updates:
        print("❌ Не найдено обновлений. Убедитесь, что вы отправили /start боту.")
        return
    
    print(f"📨 Найдено {len(updates)} обновлений:")
    print()
    
    chat_ids = set()
    
    for update in updates:
        message = update.get("message", {})
        chat = message.get("chat", {})
        chat_id = chat.get("id")
        chat_type = chat.get("type")
        username = chat.get("username", "Нет username")
        first_name = chat.get("first_name", "")
        last_name = chat.get("last_name", "")
        
        if chat_id:
            chat_ids.add(chat_id)
            print(f"💬 Чат ID: {chat_id}")
            print(f"   Тип: {chat_type}")
            print(f"   Пользователь: {first_name} {last_name} (@{username})")
            print(f"   Сообщение: {message.get('text', 'Нет текста')}")
            print()
    
    if chat_ids:
        print("🎯 Найденные Chat ID:")
        for chat_id in chat_ids:
            print(f"   {chat_id}")
        
        print()
        test_chat = list(chat_ids)[0]
        print(f"🧪 Отправляем тестовое сообщение в чат {test_chat}...")
        
        if send_test_message(test_chat):
            print()
            print("✅ Успех! Сохраните этот chat_id для настройки уведомлений:")
            print(f"   CHAT_ID = {test_chat}")
        else:
            print("❌ Не удалось отправить тестовое сообщение")
    else:
        print("❌ Не найдено chat_id в обновлениях")

if __name__ == "__main__":
    main() 