import asyncio
import json
import logging
import os
import pickle
import random
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import threading
from collections import defaultdict

from telethon.sync import TelegramClient, errors
from telethon.tl import types
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
from telethon.tl.functions.users import GetFullUserRequest

# Импортируем систему уведомлений
try:
    from telegram_notifications import notifier, check_system_status
    NOTIFICATIONS_ENABLED = True
except ImportError:
    NOTIFICATIONS_ENABLED = False
    notifier = None
    check_system_status = None

# Импортируем функции из основного модуля
import importlib.util
spec = importlib.util.spec_from_file_location("telegram_checker", "telegram-checker.py")
telegram_checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(telegram_checker)
TelegramUser = telegram_checker.TelegramUser
get_enhanced_user_status = telegram_checker.get_enhanced_user_status
validate_phone_number = telegram_checker.validate_phone_number
validate_username = telegram_checker.validate_username

logger = logging.getLogger(__name__)

@dataclass
class AccountConfig:
    """Конфигурация одного Telegram аккаунта"""
    name: str
    api_id: str
    api_hash: str
    phone: str
    session_file: str
    enabled: bool = True
    max_requests_per_hour: int = 50
    current_requests: int = 0
    last_reset: float = 0
    last_used: float = 0
    errors_count: int = 0
    flood_wait_until: float = 0
    in_use: bool = False  # Флаг "в использовании"

class MultiAccountManager:
    """Менеджер для управления множественными Telegram аккаунтами"""
    
    def __init__(self, config_file: str = "multi_account_config.json"):
        self.config_file = Path(config_file)
        self.accounts: Dict[str, AccountConfig] = {}
        self.clients: Dict[str, TelegramClient] = {}
        self.clients_ready: Dict[str, bool] = {}
        self.lock = threading.Lock()
        self.load_config()
        
    def load_config(self):
        """Загружает конфигурацию аккаунтов из файла"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for acc_data in data.get('accounts', []):
                        account = AccountConfig(**acc_data)
                        self.accounts[account.name] = account
                logger.info(f"Loaded {len(self.accounts)} accounts from config")
            except Exception as e:
                logger.error(f"Error loading config: {e}")
        else:
            logger.info("No config file found, creating default")
            self.create_default_config()
    
    def save_config(self):
        """Сохраняет конфигурацию аккаунтов в файл"""
        try:
            data = {
                'accounts': [asdict(acc) for acc in self.accounts.values()]
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info("Config saved successfully")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def create_default_config(self):
        """Создает пример конфигурации"""
        example_account = AccountConfig(
            name="account1",
            api_id="your_api_id_1",
            api_hash="your_api_hash_1", 
            phone="+1234567890",
            session_file="session_account1.session"
        )
        self.accounts[example_account.name] = example_account
        self.save_config()
        logger.info("Created default config file. Please edit it with your account details.")
    
    async def initialize_all_clients(self):
        """Инициализирует все клиенты"""
        tasks = []
        for account_name, account in self.accounts.items():
            if account.enabled:
                task = asyncio.create_task(self.initialize_client(account_name))
                tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info(f"Initialized {len([c for c in self.clients_ready.values() if c])} clients")
        else:
            logger.warning("No enabled accounts found")
    
    async def initialize_client(self, account_name: str):
        """Инициализирует один клиент"""
        account = self.accounts[account_name]
        
        # Проверяем, что аккаунт включен
        if not account.enabled:
            logger.info(f"Skipping disabled account {account_name}")
            return
        
        try:
            # Проверяем, существует ли уже сессия
            session_path = Path(account.session_file)
            if not session_path.exists():
                logger.info(f"Session file for {account_name} doesn't exist, skipping")
                return
            
            # Создаем клиент только для включенных аккаунтов
            client = TelegramClient(
                account.session_file,
                int(account.api_id),
                account.api_hash
            )
            
            await client.start(phone=account.phone)
            
            if await client.is_user_authorized():
                self.clients[account_name] = client
                self.clients_ready[account_name] = True
                logger.info(f"Client {account_name} initialized successfully")
            else:
                logger.error(f"Client {account_name} not authorized")
                self.clients_ready[account_name] = False
                
        except Exception as e:
            logger.error(f"Error initializing client {account_name}: {e}")
            self.clients_ready[account_name] = False
    
    def get_available_account(self) -> Optional[str]:
        """Возвращает доступный аккаунт для использования"""
        current_time = time.time()
        
        # Используем блокировку для предотвращения одновременного выбора одного аккаунта
        with self.lock:
            available_accounts = []
            
            for account_name, account in self.accounts.items():
                if not account.enabled:
                    continue
                    
                if account_name not in self.clients_ready or not self.clients_ready[account_name]:
                    continue
                
                # Проверяем FloodWait
                if current_time < account.flood_wait_until:
                    continue
                
                # Сбрасываем счетчик запросов и ошибок каждый час
                if current_time - account.last_reset > 3600:
                    account.current_requests = 0
                    account.errors_count = 0  # Сбрасываем счетчик ошибок
                    account.last_reset = current_time
                
                # Проверяем лимит запросов и что аккаунт не в использовании
                if account.current_requests < account.max_requests_per_hour and not account.in_use:
                    available_accounts.append(account_name)
            
            if available_accounts:
                # Улучшенная логика выбора аккаунта
                # 1. Сначала выбираем аккаунты с минимальным количеством запросов
                min_requests = min(self.accounts[name].current_requests for name in available_accounts)
                candidates = [name for name in available_accounts 
                            if self.accounts[name].current_requests == min_requests]
                
                # 2. Из кандидатов выбираем тот, который дольше не использовался
                if len(candidates) > 1:
                    selected = max(candidates, 
                                 key=lambda x: current_time - self.accounts[x].last_used)
                else:
                    selected = candidates[0]
                
                # 3. Проверяем минимальную задержку между запросами (5 секунд)
                if current_time - self.accounts[selected].last_used < 5:
                    # Если последний запрос был менее 5 секунд назад, ищем другой аккаунт
                    other_candidates = [name for name in available_accounts 
                                      if name != selected and 
                                      current_time - self.accounts[name].last_used >= 5]
                    if other_candidates:
                        selected = max(other_candidates, 
                                     key=lambda x: current_time - self.accounts[x].last_used)
                    else:
                        # Если нет других кандидатов, все равно используем выбранный
                        # (уменьшаем строгость)
                        pass
                
                # Обновляем статистику и помечаем как "в использовании"
                self.accounts[selected].current_requests += 1
                self.accounts[selected].last_used = current_time
                self.accounts[selected].in_use = True
                
                return selected
        
        # Проверяем статус системы и отправляем уведомления при проблемах
        if NOTIFICATIONS_ENABLED and check_system_status:
            try:
                status_data = self.get_status()
                check_system_status(status_data)
            except Exception as e:
                logger.error(f"Error checking system status: {e}")
        
        return None
    
    def release_account(self, account_name: str):
        """Освобождает аккаунт после использования"""
        with self.lock:
            if account_name in self.accounts:
                self.accounts[account_name].in_use = False
    
    def mark_account_error(self, account_name: str, error: Exception):
        """Отмечает ошибку для аккаунта"""
        with self.lock:
            if account_name in self.accounts:
                account = self.accounts[account_name]
                account.errors_count += 1
                
                # Если FloodWait, устанавливаем время ожидания
                if "FloodWaitError" in str(type(error)):
                    try:
                        # Извлекаем время ожидания из ошибки
                        wait_time = int(str(error).split('A wait of ')[1].split(' seconds')[0])
                        account.flood_wait_until = time.time() + wait_time + 60  # +60 для безопасности
                        logger.warning(f"Account {account_name} got FloodWait for {wait_time} seconds")
                        
                        # Отправляем детальное уведомление о FloodWait
                        if NOTIFICATIONS_ENABLED and notifier:
                            # Получаем статистику аккаунта
                            requests_this_hour = account.current_requests
                            max_requests = account.max_requests_per_hour
                            errors_count = account.errors_count
                            last_used_time = datetime.fromtimestamp(account.last_used).strftime('%H:%M:%S')
                            
                            message = f"🔴 <b>FLOODWAIT БЛОКИРОВКА</b>\n\n"
                            message += f"📱 Аккаунт: {account_name}\n"
                            message += f"⏳ Время блокировки: {wait_time} сек\n"
                            message += f"📊 Запросов в этом часе: {requests_this_hour}/{max_requests}\n"
                            message += f"❌ Всего ошибок: {errors_count}\n"
                            message += f"🕐 Последний запрос: {last_used_time}\n"
                            message += f"📈 Использование: {requests_this_hour/max_requests*100:.1f}%"
                            
                            notifier.send_warning_alert(message)
                    except:
                        account.flood_wait_until = time.time() + 3600  # 1 час по умолчанию
                
                # Если много ошибок, временно отключаем аккаунт
                if account.errors_count > 20:  # Увеличиваем лимит ошибок
                    account.enabled = False
                    logger.warning(f"Account {account_name} disabled due to too many errors")
                    
                    # Отправляем уведомление о критической ошибке
                    if NOTIFICATIONS_ENABLED and notifier:
                        notifier.send_critical_alert(f"❌ Аккаунт {account_name} отключен из-за {account.errors_count} ошибок")
    
    async def check_phone_with_account(self, account_name: str, phone: str) -> Optional[TelegramUser]:
        """Проверяет номер телефона с конкретным аккаунтом"""
        if account_name not in self.clients:
            return None
            
        client = self.clients[account_name]
        
        try:
            # Валидируем номер
            validated_phone = validate_phone_number(phone)
            if not validated_phone:
                return None
            
            # Импортируем контакт
            contact = types.InputPhoneContact(
                client_id=random.randint(0, 999999999),
                phone=validated_phone,
                first_name="Check",
                last_name="User"
            )
            
            result = await client(ImportContactsRequest([contact]))
            
            if result.users:
                user = result.users[0]
                telegram_user = await TelegramUser.from_user(client, user, validated_phone)
                
                # Удаляем контакт
                await client(DeleteContactsRequest([user.id]))
                
                return telegram_user
            else:
                return None
                
        except Exception as e:
            # Проверяем, является ли это нормальной ошибкой (пользователь не найден)
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ['no user', 'nobody is using', 'not found']):
                # Это нормальная ошибка, не увеличиваем счетчик
                logger.info(f"Phone {phone}: No user found (normal)")
                return None
            else:
                # Это реальная ошибка - ВСЕГДА помечаем как ошибку аккаунта
                self.mark_account_error(account_name, e)
                logger.error(f"Error checking phone {phone} with account {account_name}: {e}")
                return None
    
    async def check_username_with_account(self, account_name: str, username: str) -> Optional[TelegramUser]:
        """Проверяет username с конкретным аккаунтом"""
        if account_name not in self.clients:
            return None
            
        client = self.clients[account_name]
        
        try:
            # Валидируем username
            validated_username = validate_username(username)
            if not validated_username:
                return None
            
            # Получаем пользователя
            user = await client.get_entity(validated_username)
            
            if user:
                # Проверяем, что это пользователь, а не канал
                if hasattr(user, 'status'):  # Это User
                    telegram_user = await TelegramUser.from_user(client, user, "")
                    return telegram_user
                else:
                    # Это Channel или что-то другое
                    logger.warning(f"Username {validated_username} is not a user (probably a channel)")
                    return None
            else:
                return None
                
        except Exception as e:
            # Проверяем, является ли это нормальной ошибкой (пользователь не найден)
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ['no user', 'nobody is using', 'not found', 'unacceptable']):
                # Это нормальная ошибка, не увеличиваем счетчик
                logger.info(f"Username {username}: No user found (normal)")
                return None
            else:
                # Это реальная ошибка - ВСЕГДА помечаем как ошибку аккаунта
                self.mark_account_error(account_name, e)
                logger.error(f"Error checking username {username} with account {account_name}: {e}")
                return None
    
    async def process_phones_distributed(self, phones: List[str]) -> Dict[str, Any]:
        """Обрабатывает список телефонов, распределяя нагрузку между аккаунтами"""
        logger.info(f"Starting batch processing of {len(phones)} phones: {phones}")
        results = {}
        
        # Создаем задачи для параллельной обработки с увеличенными задержками
        tasks = []
        for phone in phones:
            task = asyncio.create_task(self._process_single_phone(phone))
            tasks.append(task)
        
        # Ждем завершения всех задач
        phone_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Собираем результаты
        for i, result in enumerate(phone_results):
            if isinstance(result, Exception):
                results[phones[i]] = {"error": str(result)}
            else:
                results[phones[i]] = result
        
        # Добавляем задержку после завершения батча
        batch_delay = random.uniform(8, 15)  # 8-15 секунд между батчами
        logger.info(f"Completed batch processing of {len(phones)} phones, waiting {batch_delay:.1f}s before next batch")
        await asyncio.sleep(batch_delay)
        
        return results
    
    async def _process_single_phone(self, phone: str) -> Dict[str, Any]:
        """Обрабатывает один телефон с автоматическим выбором аккаунта"""
        max_retries = 15  # Увеличиваем количество попыток
        for attempt in range(max_retries):
            account_name = self.get_available_account()
            
            if not account_name:
                # Нет доступных аккаунтов, ждем
                logger.info(f"Phone {phone}: No available accounts, waiting... (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(random.uniform(1, 2))  # Случайная задержка 1-2 секунды
                continue
            
            # Добавляем случайную задержку для избежания блокировок
            delay = random.uniform(4, 8)  # Увеличиваем задержки для безопасности
            logger.info(f"Phone {phone}: Using account {account_name}, delay {delay:.1f}s")
            await asyncio.sleep(delay)
            
            try:
                logger.info(f"Phone {phone}: Starting check with {account_name}")
                result = await self.check_phone_with_account(account_name, phone)
                
                if result:
                    logger.info(f"Phone {phone}: Found user {result.username} via {account_name}")
                    return asdict(result)
                else:
                    logger.info(f"Phone {phone}: No user found via {account_name}")
                    return {"error": "No Telegram account found"}
            except Exception as e:
                logger.error(f"Phone {phone}: Error with {account_name}: {e}")
                return {"error": str(e)}
            finally:
                # Освобождаем аккаунт в любом случае
                self.release_account(account_name)
                logger.info(f"Phone {phone}: Released account {account_name}")
        
        return {"error": "No available accounts after retries"}
    
    async def process_usernames_distributed(self, usernames: List[str]) -> Dict[str, Any]:
        """Обрабатывает список username, распределяя нагрузку между аккаунтами"""
        logger.info(f"Starting batch processing of {len(usernames)} usernames: {usernames}")
        results = {}
        
        # Создаем задачи для параллельной обработки с увеличенными задержками
        tasks = []
        for username in usernames:
            # Добавляем случайную задержку старта для естественности
            start_delay = random.uniform(1.0, 5.0)  # Увеличиваем задержку старта
            task = asyncio.create_task(self._process_single_username_with_delay(username, start_delay))
            tasks.append(task)
        
        # Ждем завершения всех задач
        username_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Собираем результаты
        for i, result in enumerate(username_results):
            if isinstance(result, Exception):
                results[usernames[i]] = {"error": str(result)}
            else:
                results[usernames[i]] = result
        
        # Добавляем задержку после завершения батча
        batch_delay = random.uniform(8, 15)  # 8-15 секунд между батчами
        logger.info(f"Completed batch processing of {len(usernames)} usernames, waiting {batch_delay:.1f}s before next batch")
        await asyncio.sleep(batch_delay)
        
        return results
    
    async def _process_single_username_with_delay(self, username: str, start_delay: float) -> Dict[str, Any]:
        """Обрабатывает один username с задержкой старта для естественности"""
        # Ждем случайную задержку перед стартом
        logger.info(f"Username {username}: Starting with delay {start_delay:.1f}s")
        await asyncio.sleep(start_delay)
        
        return await self._process_single_username(username)
    
    async def _process_single_username(self, username: str) -> Dict[str, Any]:
        """Обрабатывает один username с автоматическим выбором аккаунта"""
        max_retries = 15  # Увеличиваем количество попыток
        for attempt in range(max_retries):
            account_name = self.get_available_account()
            
            if not account_name:
                # Нет доступных аккаунтов, ждем
                logger.info(f"Username {username}: No available accounts, waiting... (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(random.uniform(1, 2))  # Случайная задержка 1-2 секунды
                continue
            
            # Добавляем случайную задержку для избежания блокировок
            delay = random.uniform(4, 8)  # Увеличиваем задержки для безопасности
            logger.info(f"Username {username}: Using account {account_name}, delay {delay:.1f}s")
            await asyncio.sleep(delay)
            
            try:
                logger.info(f"Username {username}: Starting check with {account_name}")
                result = await self.check_username_with_account(account_name, username)
                
                if result:
                    logger.info(f"Username {username}: Found user {result.username} via {account_name}")
                    return asdict(result)
                else:
                    logger.info(f"Username {username}: No user found via {account_name}")
                    return {"error": "No Telegram account found"}
            except Exception as e:
                logger.error(f"Username {username}: Error with {account_name}: {e}")
                return {"error": str(e)}
            finally:
                # Освобождаем аккаунт в любом случае
                self.release_account(account_name)
                logger.info(f"Username {username}: Released account {account_name}")
        
        return {"error": "No available accounts after retries"}
    
    def get_status(self) -> Dict[str, Any]:
        """Возвращает статус всех аккаунтов"""
        status = {
            'total_accounts': len(self.accounts),
            'enabled_accounts': len([a for a in self.accounts.values() if a.enabled]),
            'ready_clients': len([c for c in self.clients_ready.values() if c]),
            'accounts': {}
        }
        
        for name, account in self.accounts.items():
            status['accounts'][name] = {
                'enabled': account.enabled,
                'ready': self.clients_ready.get(name, False),
                'current_requests': account.current_requests,
                'max_requests': account.max_requests_per_hour,
                'errors_count': account.errors_count,
                'flood_wait_until': account.flood_wait_until,
                'last_used': account.last_used
            }
        
        return status
    
    async def close_all_clients(self):
        """Закрывает все клиенты"""
        for client in self.clients.values():
            try:
                await client.disconnect()
            except:
                pass
        self.clients.clear()
        self.clients_ready.clear() 