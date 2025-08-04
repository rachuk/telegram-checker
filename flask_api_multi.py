from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import json
from dataclasses import asdict
import threading
import queue
import time
import logging

from multi_account_manager import MultiAccountManager

# Импортируем систему уведомлений
try:
    from telegram_notifications import notifier, check_system_status
    NOTIFICATIONS_ENABLED = True
except ImportError:
    NOTIFICATIONS_ENABLED = False
    notifier = None
    check_system_status = None

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("telegram_checker_multi.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Global variables for multi-account manager
account_manager = None
manager_ready = False
request_queue = queue.Queue()
response_queues = {}
worker_thread = None
last_monitoring_check = 0
monitoring_interval = 60  # Проверяем каждую минуту

def telegram_worker():
    """Background worker that maintains persistent Telegram connections"""
    global account_manager, manager_ready, last_monitoring_check
    
    async def init_manager():
        global account_manager, manager_ready
        try:
            account_manager = MultiAccountManager()
            await account_manager.initialize_all_clients()
            manager_ready = True
            logger.info("Multi-account manager initialized and ready")
            
            # Отправляем уведомление о запуске
            if NOTIFICATIONS_ENABLED and notifier:
                notifier.send_success_alert("🚀 Система Telegram Checker запущена и готова к работе")
                
        except Exception as e:
            logger.error(f"Failed to initialize multi-account manager: {e}")
            manager_ready = False
            
            # Отправляем уведомление об ошибке запуска
            if NOTIFICATIONS_ENABLED and notifier:
                notifier.send_critical_alert(f"❌ Ошибка запуска системы: {str(e)}")
    
    async def check_system_monitoring():
        """Проверяет статус системы и отправляет уведомления"""
        global last_monitoring_check
        
        current_time = time.time()
        if current_time - last_monitoring_check >= monitoring_interval:
            last_monitoring_check = current_time
            
            if account_manager and NOTIFICATIONS_ENABLED and check_system_status:
                try:
                    status_data = account_manager.get_status()
                    check_system_status(status_data)
                except Exception as e:
                    logger.error(f"Error in system monitoring: {e}")
    
    async def process_requests():
        while True:
            try:
                # Проверяем мониторинг
                await check_system_monitoring()
                
                # Get request from queue
                if not request_queue.empty():
                    request_id, phones, usernames = request_queue.get()
                    
                    # Process request
                    results = {}
                    
                    if phones:
                        # Use distributed processing for phones
                        phone_results = await account_manager.process_phones_distributed(phones)
                        results.update(phone_results)
                    
                    if usernames:
                        # Use distributed processing for usernames
                        username_results = await account_manager.process_usernames_distributed(usernames)
                        results.update(username_results)
                    
                    # Put result in response queue
                    if request_id in response_queues:
                        response_queues[request_id].put(results)
                
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
                
            except Exception as e:
                logger.error(f"Error in process_requests: {e}")
                
                # Отправляем уведомление об ошибке
                if NOTIFICATIONS_ENABLED and notifier:
                    notifier.send_warning_alert(f"⚠️ Ошибка в обработке запросов: {str(e)}")
                
                await asyncio.sleep(1)
    
    # Run the async functions
    async def main():
        await init_manager()
        if manager_ready:
            await process_requests()
    
    # Create new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except Exception as e:
        logger.error(f"Error in telegram_worker: {e}")
    finally:
        loop.close()

def start_telegram_worker():
    """Start the background Telegram worker thread"""
    global worker_thread
    if worker_thread is None or not worker_thread.is_alive():
        worker_thread = threading.Thread(target=telegram_worker, daemon=True)
        worker_thread.start()
        
        # Wait for manager to be ready
        timeout = 60  # Увеличиваем timeout для инициализации множественных аккаунтов
        for _ in range(timeout):
            if manager_ready:
                break
            time.sleep(1)

def make_telegram_request(phones=None, usernames=None, timeout=120):
    """Make a request to the Telegram worker"""
    if not manager_ready:
        return {"error": "Multi-account manager not ready"}
    
    request_id = str(time.time())
    response_queue = queue.Queue()
    response_queues[request_id] = response_queue
    
    try:
        # Put request in queue
        request_queue.put((request_id, phones, usernames))
        
        # Wait for response
        try:
            result = response_queue.get(timeout=timeout)
            return result
        except queue.Empty:
            return {"error": "Request timeout"}
    
    finally:
        # Clean up
        if request_id in response_queues:
            del response_queues[request_id]

@app.route('/check_phones', methods=['POST'])
def check_phones():
    phones = request.json.get('phones', [])
    
    try:
        result = make_telegram_request(phones=phones)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/check_usernames', methods=['POST'])
def check_usernames():
    data = request.json
    if isinstance(data, list):
        usernames = data
    else:
        usernames = data.get('usernames', [])
    
    try:
        result = make_telegram_request(usernames=usernames)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    global account_manager, manager_ready
    
    # Проверяем мониторинг при каждом health check
    if account_manager and NOTIFICATIONS_ENABLED and check_system_status:
        try:
            status_data = account_manager.get_status()
            check_system_status(status_data)
        except Exception as e:
            logger.error(f"Error in health check monitoring: {e}")
    
    if not manager_ready:
        return jsonify({
            "status": "error",
            "message": "Telegram manager not ready",
            "telegram_ready": False
        }), 503
    
    return jsonify({
        "status": "ok",
        "message": "API is running",
        "telegram_ready": manager_ready
    })

@app.route('/accounts/status', methods=['GET'])
def accounts_status():
    """Подробный статус всех аккаунтов"""
    if not manager_ready or not account_manager:
        return jsonify({"error": "Manager not ready"}), 503
    
    return jsonify(account_manager.get_status())

@app.route('/accounts/reload', methods=['POST'])
def reload_accounts():
    """Перезагружает конфигурацию аккаунтов"""
    global manager_ready
    try:
        if account_manager:
            account_manager.save_config()
            # Перезапускаем воркер для применения изменений
            manager_ready = False
            start_telegram_worker()
        
        return jsonify({"status": "ok", "message": "Accounts reload initiated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/restart_client', methods=['POST'])
def restart_client():
    """Restart the Telegram client"""
    global manager_ready
    manager_ready = False
    start_telegram_worker()
    return jsonify({"status": "ok", "message": "Client restart initiated"})

@app.route('/test_speed', methods=['GET'])
def test_speed():
    """Quick speed test endpoint"""
    import time
    start_time = time.time()
    
    # Simulate quick processing
    time.sleep(0.1)
    
    processing_time = time.time() - start_time
    
    return jsonify({
        "status": "ok",
        "message": "Speed test completed",
        "processing_time": f"{processing_time:.3f}s",
        "server_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "manager_ready": manager_ready
    })

@app.route('/check_and_webhook', methods=['POST'])
def check_and_webhook():
    """Check phones/usernames and send results to webhook"""
    import requests
    
    data = request.json
    phones = data.get('phones', [])
    usernames = data.get('usernames', [])
    webhook_url = data.get('webhook_url')
    
    if not webhook_url:
        return jsonify({"error": "webhook_url required"}), 400
    
    try:
        # Process telegram check
        if phones:
            result = make_telegram_request(phones=phones)
        elif usernames:
            result = make_telegram_request(usernames=usernames)
        else:
            result = {"error": "phones or usernames required"}
        
        # Send to webhook
        webhook_response = requests.post(
            webhook_url, 
            json=result, 
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        return jsonify({
            "status": "ok",
            "message": "Results sent to webhook",
            "webhook_status": webhook_response.status_code
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/batch_check', methods=['POST'])
def batch_check():
    """Проверяет большие списки с прогрессом"""
    data = request.json
    phones = data.get('phones', [])
    usernames = data.get('usernames', [])
    batch_size = data.get('batch_size', 10)
    
    if not phones and not usernames:
        return jsonify({"error": "phones or usernames required"}), 400
    
    try:
        all_results = {}
        total_items = len(phones) + len(usernames)
        processed = 0
        
        # Обрабатываем телефоны батчами
        if phones:
            for i in range(0, len(phones), batch_size):
                batch = phones[i:i + batch_size]
                batch_result = make_telegram_request(phones=batch)
                all_results.update(batch_result)
                processed += len(batch)
                logger.info(f"Processed {processed}/{total_items} items")
        
        # Обрабатываем username батчами
        if usernames:
            for i in range(0, len(usernames), batch_size):
                batch = usernames[i:i + batch_size]
                batch_result = make_telegram_request(usernames=batch)
                all_results.update(batch_result)
                processed += len(batch)
                logger.info(f"Processed {processed}/{total_items} items")
        
        return jsonify({
            "status": "ok",
            "total_processed": processed,
            "results": all_results
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/monitoring/check', methods=['POST'])
def force_monitoring_check():
    """Принудительная проверка статуса системы"""
    global account_manager
    
    if not account_manager:
        return jsonify({
            "status": "error",
            "message": "Account manager not initialized"
        }), 503
    
    try:
        status_data = account_manager.get_status()
        
        if NOTIFICATIONS_ENABLED and check_system_status:
            check_system_status(status_data)
        
        return jsonify({
            "status": "ok",
            "message": "Monitoring check completed",
            "data": status_data
        })
        
    except Exception as e:
        logger.error(f"Error in force monitoring check: {e}")
        return jsonify({
            "status": "error",
            "message": f"Monitoring check failed: {str(e)}"
        }), 500

@app.route('/monitoring/status', methods=['GET'])
def get_monitoring_status():
    """Получить текущий статус мониторинга"""
    global account_manager, last_monitoring_check
    
    if not account_manager:
        return jsonify({
            "status": "error",
            "message": "Account manager not initialized"
        }), 503
    
    try:
        status_data = account_manager.get_status()
        
        # Анализируем статус
        total_enabled = 0
        available_accounts = 0
        flood_wait_accounts = []
        
        for account_name, account_data in status_data.get("accounts", {}).items():
            if account_data.get("enabled"):
                total_enabled += 1
                
                # Проверяем, истекло ли время FloodWait
                flood_wait_until = account_data.get("flood_wait_until", 0)
                current_time = time.time()
                
                if account_data.get("ready") and flood_wait_until <= current_time:
                    available_accounts += 1
                elif flood_wait_until > current_time:
                    flood_wait_accounts.append(account_name)
        
        monitoring_status = {
            "notifications_enabled": NOTIFICATIONS_ENABLED,
            "last_check": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_monitoring_check)),
            "total_enabled_accounts": total_enabled,
            "available_accounts": available_accounts,
            "flood_wait_accounts": flood_wait_accounts,
            "system_status": "critical" if available_accounts == 0 else "warning" if flood_wait_accounts else "ok"
        }
        
        return jsonify(monitoring_status)
        
    except Exception as e:
        logger.error(f"Error getting monitoring status: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to get monitoring status: {str(e)}"
        }), 500

if __name__ == '__main__':
    print("Starting Multi-Account Telegram API...")
    start_telegram_worker()
    
    app.run(host='0.0.0.0', port=5000, threaded=True) 