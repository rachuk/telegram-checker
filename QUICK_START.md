# 🚀 Быстрый старт - Множественные Telegram аккаунты

## Для проверки 17000 контактов

### 1. Быстрая настройка
```bash
# Запустите быстрый старт
python quick_start_multi.py

# Выберите "4. Запустить настройку аккаунтов"
# Добавьте ваши Telegram аккаунты
```

### 2. Подготовка аккаунтов
- Создайте **5-20 Telegram аккаунтов**
- Получите **API ID и Hash** для каждого на https://my.telegram.org/apps
- Для каждого аккаунта нужны: API ID, API Hash, номер телефона

### 3. Настройка системы
```bash
python setup_multi_accounts.py

# Добавьте каждый аккаунт:
# - Название: account1, account2, etc.
# - API ID и Hash
# - Номер телефона
# - Протестируйте подключение
```

### 4. Запуск API
```bash
# Запустите API
python flask_api_multi.py

# Или через systemd
sudo cp telegram-checker-multi.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable telegram-checker-multi
sudo systemctl start telegram-checker-multi
```

### 5. Массовая проверка
```bash
# Подготовьте файл с контактами (TXT/CSV/JSON)
# Запустите массовую проверку
python bulk_checker.py

# Введите:
# - Путь к файлу с 17000 контактами
# - Размер батча: 10
# - Сохранение прогресса: y
```

## 📊 Производительность

| Аккаунтов | Запросов/час | Время для 17000 |
|-----------|--------------|-----------------|
| 5         | 150-250      | 7-12 дней       |
| 10        | 300-500      | 3.5-6 дней      |
| 20        | 600-1000     | 1.7-3 дня       |

## 🔧 Мониторинг

```bash
# Проверка здоровья
curl http://localhost:5000/health

# Статус аккаунтов  
curl http://localhost:5000/accounts/status

# Логи
tail -f telegram_checker_multi.log
```

## 📁 Результаты

Результаты сохраняются в:
- `bulk_results/bulk_check_YYYYMMDD_HHMMSS.json` - полные данные
- `bulk_results/bulk_check_YYYYMMDD_HHMMSS.csv` - для Excel
- `bulk_results/progress_YYYYMMDD_HHMMSS.json` - прогресс

## ⚠️ Важно

- **Не более 50 запросов/час** на аккаунт
- **Мониторьте логи** на предмет блокировок
- **Используйте резервные аккаунты**
- **Сохраняйте прогресс** для больших объемов

---

**Удачной проверки! 🎯** 