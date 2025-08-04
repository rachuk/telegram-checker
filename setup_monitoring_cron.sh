#!/bin/bash
# Скрипт для настройки автоматического мониторинга

echo "🔧 Настройка автоматического мониторинга..."

# Создаем cron job для проверки каждые 5 минут
(crontab -l 2>/dev/null; echo "*/5 * * * * cd /root/telegram-checker && python3 check_all_accounts.py >> /root/telegram-checker/monitoring.log 2>&1") | crontab -

# Создаем cron job для ежедневного отчета в 9:00
(crontab -l 2>/dev/null; echo "0 9 * * * cd /root/telegram-checker && python3 telegram_notifications.py report >> /root/telegram-checker/daily_report.log 2>&1") | crontab -

echo "✅ Cron jobs добавлены:"
echo "   - Проверка каждые 5 минут"
echo "   - Ежедневный отчет в 9:00"
echo ""
echo "📋 Текущие cron jobs:"
crontab -l

echo ""
echo "📝 Логи будут сохраняться в:"
echo "   - /root/telegram-checker/monitoring.log"
echo "   - /root/telegram-checker/daily_report.log" 