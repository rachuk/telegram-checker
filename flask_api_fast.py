from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import json
from dataclasses import asdict
import importlib.util
import threading
import queue
import time

# Import TelegramChecker
spec = importlib.util.spec_from_file_location("telegram_checker", "telegram-checker.py")
telegram_checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(telegram_checker)
TelegramChecker = telegram_checker.TelegramChecker

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Global variables for persistent connection
telegram_client = None
client_ready = False
request_queue = queue.Queue()
response_queues = {}
worker_thread = None

def telegram_worker():
    """Background worker that maintains persistent Telegram connection"""
    global telegram_client, client_ready
    
    async def init_client():
        global telegram_client, client_ready
        try:
            telegram_client = TelegramChecker()
            await telegram_client.initialize()
            client_ready = True
            print("Telegram client initialized and ready")
        except Exception as e:
            print(f"Failed to initialize Telegram client: {e}")
            client_ready = False
    
    async def process_requests():
        while True:
            try:
                # Get request from queue
                if not request_queue.empty():
                    request_id, phones, usernames = request_queue.get()
                    
                    # Process request
                    results = {}
                    
                    if phones:
                        # Use the process_phones function with delays
                        phone_results = await telegram_client.process_phones(phones)
                        results.update(phone_results)
                    
                    if usernames:
                        # Use the process_usernames function with delays
                        username_results = await telegram_client.process_usernames(usernames)
                        results.update(username_results)
                    
                    # Put result in response queue
                    if request_id in response_queues:
                        response_queues[request_id].put(results)
                
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
                
            except Exception as e:
                print(f"Error in process_requests: {e}")
                await asyncio.sleep(1)
    
    # Run the async functions
    async def main():
        await init_client()
        if client_ready:
            await process_requests()
    
    # Create new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except Exception as e:
        print(f"Error in telegram_worker: {e}")
    finally:
        loop.close()

def start_telegram_worker():
    """Start the background Telegram worker thread"""
    global worker_thread
    if worker_thread is None or not worker_thread.is_alive():
        worker_thread = threading.Thread(target=telegram_worker, daemon=True)
        worker_thread.start()
        
        # Wait for client to be ready
        timeout = 30
        for _ in range(timeout):
            if client_ready:
                break
            time.sleep(1)

def make_telegram_request(phones=None, usernames=None, timeout=30):
    """Make a request to the Telegram worker"""
    if not client_ready:
        return {"error": "Telegram client not ready"}
    
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
    usernames = request.json.get('usernames', [])
    
    try:
        result = make_telegram_request(usernames=usernames)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "ok" if client_ready else "initializing",
        "message": "API is running",
        "telegram_connected": client_ready
    })

@app.route('/restart_client', methods=['POST'])
def restart_client():
    """Restart the Telegram client"""
    global client_ready
    client_ready = False
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
        "telegram_ready": client_ready
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

if __name__ == '__main__':
    print("Starting Telegram API with persistent connection...")
    start_telegram_worker()
    
    app.run(host='0.0.0.0', port=5000, threaded=True) 