# 📱 Telegram Account Checker - Multi-Account System

**Мощная система проверки Telegram аккаунтов с поддержкой множественных юзерботов для обработки больших объемов данных!**

## 🚀 Основные возможности

- 🔄 **Множественные аккаунты** - распределение нагрузки между несколькими юзерботами
- ⚡ **Автоматический балансировщик** - умное распределение запросов
- 🛡️ **FloodWait защита** - автоматическое переключение при блокировках
- 📊 **Массовая обработка** - до 17000+ контактов за раз
- 💾 **Сохранение прогресса** - возможность возобновления работы
- 📈 **Детальная статистика** - мониторинг всех аккаунтов

## 📈 Производительность

### С одним аккаунтом:
- ~30-50 запросов/час
- 17000 контактов = ~14-23 дня

### С 10 аккаунтами:
- ~300-500 запросов/час
- 17000 контактов = ~1.4-2.3 дня

### С 20 аккаунтами:
- ~600-1000 запросов/час  
- 17000 контактов = ~17-28 часов

## 🛠️ Установка и настройка

### 1. Подготовка аккаунтов
```bash
# Создайте несколько Telegram аккаунтов
# Получите API ID и Hash для каждого на https://my.telegram.org/apps
```

### 2. Настройка системы
```bash
# Клонируйте репозиторий
git clone <repository>
cd telegram-checker

# Установите зависимости
pip install -r requirements.txt

# Настройте аккаунты
python setup_multi_accounts.py
```

### 3. Настройка аккаунтов
```bash
# Запустите интерактивную настройку
python setup_multi_accounts.py

# Следуйте инструкциям:
# 1. Добавьте каждый аккаунт
# 2. Введите API ID, Hash, телефон
# 3. Протестируйте подключение
# 4. Сохраните конфигурацию
```

### 4. Запуск API
```bash
# Запустите API с множественными аккаунтами
python flask_api_multi.py

# Или через systemd
sudo cp telegram-checker-multi.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable telegram-checker-multi
sudo systemctl start telegram-checker-multi
```

## 📋 Конфигурация аккаунтов

Файл `multi_account_config.json`:
```json
{
  "accounts": [
    {
      "name": "account1",
      "api_id": "123456",
      "api_hash": "abcdef1234567890abcdef1234567890",
      "phone": "+1234567890",
      "session_file": "session_account1.session",
      "enabled": true,
      "max_requests_per_hour": 50
    },
    {
      "name": "account2", 
      "api_id": "654321",
      "api_hash": "fedcba0987654321fedcba0987654321",
      "phone": "+0987654321",
      "session_file": "session_account2.session",
      "enabled": true,
      "max_requests_per_hour": 50
    }
  ]
}
```

## 🔧 API Endpoints

### Проверка здоровья системы
```bash
GET /health
```
**Ответ:**
```json
{
  "status": "ok",
  "message": "Multi-account API is running",
  "manager_ready": true,
  "total_accounts": 5,
  "enabled_accounts": 5,
  "ready_clients": 5,
  "accounts": {
    "account1": {
      "enabled": true,
      "ready": true,
      "current_requests": 15,
      "max_requests": 50,
      "errors_count": 0
    }
  }
}
```

### Статус аккаунтов
```bash
GET /accounts/status
```

### Перезагрузка конфигурации
```bash
POST /accounts/reload
```

### Массовая проверка
```bash
POST /batch_check
Content-Type: application/json

{
  "phones": ["+1234567890", "+9876543210"],
  "batch_size": 10
}
```

## 🚀 Массовая обработка

### Через скрипт
```bash
# Запустите массовую проверку
python bulk_checker.py

# Введите:
# - Путь к файлу с контактами
# - Размер батча (рекомендуется 10)
# - Сохранение прогресса
```

### Поддерживаемые форматы файлов:
- **CSV**: `contacts.csv`
- **TXT**: `contacts.txt` (по одному контакту на строку)
- **JSON**: `contacts.json`

### Пример файла контактов:
```txt
+1234567890
+9876543210
username1
username2
```

## 📊 Мониторинг и статистика

### Просмотр логов
```bash
# Логи API
tail -f telegram_checker_multi.log

# Логи systemd
journalctl -u telegram-checker-multi -f
```

### Статистика аккаунтов
```bash
# Проверка статуса
curl http://localhost:5000/accounts/status | jq

# Проверка здоровья
curl http://localhost:5000/health | jq
```

## 🔄 Управление аккаунтами

### Добавление нового аккаунта
```bash
python setup_multi_accounts.py
# Выберите "1. Добавить новый аккаунт"
```

### Отключение аккаунта
```bash
python setup_multi_accounts.py
# Выберите "5. Редактировать аккаунт"
# Отключите аккаунт
```

### Перезагрузка конфигурации
```bash
curl -X POST http://localhost:5000/accounts/reload
```

## 🛡️ Безопасность и ограничения

### Автоматическая защита
- **FloodWait обработка** - автоматическое переключение на другой аккаунт
- **Лимиты запросов** - настраиваемые лимиты для каждого аккаунта
- **Обработка ошибок** - автоматическое отключение проблемных аккаунтов

### Рекомендации
- **Не более 50 запросов/час** на аккаунт
- **Случайные задержки** 2-8 секунд между запросами
- **Мониторинг логов** для выявления проблем
- **Резервные аккаунты** для высокой доступности

## 📈 Оптимизация производительности

### Для 17000 контактов:

**Минимальная конфигурация (5 аккаунтов):**
- Время: ~7-12 дней
- Рекомендуется для тестирования

**Рекомендуемая конфигурация (10 аккаунтов):**
- Время: ~3.5-6 дней
- Оптимальное соотношение скорость/риск

**Высокопроизводительная конфигурация (20 аккаунтов):**
- Время: ~1.7-3 дня
- Требует больше ресурсов

### Настройки батчей:
- **Размер батча**: 10-20 контактов
- **Задержка между батчами**: 1-2 секунды
- **Таймаут запроса**: 120 секунд

## 🔧 Устранение неполадок

### Аккаунт не подключается
```bash
# Проверьте конфигурацию
python setup_multi_accounts.py
# Выберите "3. Тестировать все аккаунты"

# Проверьте логи
tail -f telegram_checker_multi.log
```

### FloodWait ошибки
- Система автоматически обрабатывает
- Проверьте статус аккаунтов: `GET /accounts/status`
- При необходимости добавьте больше аккаунтов

### Медленная работа
- Увеличьте количество аккаунтов
- Проверьте лимиты запросов
- Убедитесь в стабильности интернета

## 📝 Примеры использования

### Python клиент
```python
import requests

def check_contacts_bulk(contacts, batch_size=10):
    results = {}
    
    for i in range(0, len(contacts), batch_size):
        batch = contacts[i:i + batch_size]
        
        response = requests.post(
            'http://localhost:5000/batch_check',
            json={'phones': batch, 'batch_size': batch_size},
            timeout=120
        )
        
        if response.status_code == 200:
            batch_results = response.json()
            results.update(batch_results['results'])
        
        print(f"Обработано: {len(results)}/{len(contacts)}")
    
    return results

# Использование
contacts = ["+1234567890", "+9876543210"]  # 17000 контактов
results = check_contacts_bulk(contacts)
```

### cURL примеры
```bash
# Проверка здоровья
curl http://localhost:5000/health

# Статус аккаунтов
curl http://localhost:5000/accounts/status

# Массовая проверка
curl -X POST http://localhost:5000/batch_check \
  -H "Content-Type: application/json" \
  -d '{"phones": ["+1234567890"], "batch_size": 10}'
```

## ⚠️ Важные замечания

- **Соблюдайте лимиты** Telegram API
- **Мониторьте аккаунты** на предмет блокировок
- **Сохраняйте прогресс** для больших объемов
- **Используйте резервные аккаунты**
- **Соблюдайте правила** использования Telegram

## 🎯 Результаты

Система сохраняет результаты в:
- **JSON файл** - полные данные
- **CSV файл** - для анализа в Excel
- **Прогресс файл** - для возобновления работы

### Структура результатов:
```json
{
  "+1234567890": {
    "id": 123456789,
    "username": "user123",
    "first_name": "John",
    "last_name": "Doe",
    "premium": true,
    "verified": false,
    "bot": false,
    "last_seen": "Last seen: 2025-01-30 10:30:45 UTC",
    "bio": "User bio..."
  }
}
```

---

**Удачной проверки! 🎯** 