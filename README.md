# 📱 Telegram Account Checker API

Enhanced Telegram account validation service with Flask API, persistent connections, and systemd integration!

## ✨ Features

- 🔍 **REST API** for checking phone numbers and usernames
- 🔄 **Persistent Telegram connection** with background worker
- 🚀 **Systemd service** for automatic startup and restart
- ⚡ **Adaptive rate limiting** to avoid FloodWait errors
- 📊 **Detailed user information** including premium status, verification, bio
- 🔐 **Secure credential storage** with session management
- 🌐 **CORS enabled** for web integration
- 📝 **Comprehensive logging** to `telegram_checker.log`

## 🚀 Quick Start

### 1. Installation
```bash
git clone <repository>
cd telegram-checker
pip install -r requirements.txt
```

### 2. First Time Setup
```bash
# Start manually to create session
source venv/bin/activate
python flask_api_fast.py

# Enter your Telegram API credentials when prompted:
# - API ID (from https://my.telegram.org/apps)
# - API Hash
# - Phone number with country code
# - Verification code (sent to Telegram)

# After successful authorization, stop with Ctrl+C
```

### 3. Setup Systemd Service
```bash
# Copy service file
cp telegram-checker.service /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

# Enable and start service
systemctl enable telegram-checker
systemctl start telegram-checker

# Check status
systemctl status telegram-checker
```

## 🌐 API Endpoints

### Health Check
```bash
GET /health
```
**Response:**
```json
{
  "message": "API is running",
  "status": "ok",
  "telegram_connected": true
}
```

### Check Phone Numbers
```bash
POST /check_phones
Content-Type: application/json

{
  "phones": ["+1234567890", "+9876543210"]
}
```

### Check Usernames
```bash
POST /check_usernames
Content-Type: application/json

{
  "usernames": ["username1", "username2"]
}
```

### Restart Service
```bash
POST /restart_client
```

### Speed Test
```bash
GET /test_speed
```

## 📊 Response Format

### Successful Check
```json
{
  "+1234567890": {
    "id": 123456789,
    "username": "example_user",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1234567890",
    "premium": true,
    "verified": false,
    "fake": false,
    "bot": false,
    "last_seen": "Last seen: 2025-07-30 10:30:45 UTC",
    "last_seen_exact": "2025-07-30 10:30:45 UTC",
    "status_type": "offline",
    "bio": "User bio here...",
    "common_chats_count": 2,
    "blocked": false,
    "profile_photos": [],
    "privacy_restricted": false
  }
}
```

### Not Found
```json
{
  "+1234567890": {
    "error": "No Telegram account found"
  }
}
```

### Invalid Format
```json
{
  "invalid_phone": {
    "error": "Invalid phone number format: invalid_phone"
  }
}
```

## ⚙️ Configuration

### Environment Variables
- `API_ID` - Telegram API ID
- `API_HASH` - Telegram API Hash
- `PHONE` - Your phone number

### Rate Limiting
The service automatically handles Telegram rate limits:
- **Adaptive delays** between requests (2-8 seconds)
- **FloodWait handling** with automatic retry
- **Batch processing** with configurable limits

### Logging
- **File**: `telegram_checker.log`
- **Console**: Real-time output
- **Systemd**: `journalctl -u telegram-checker`

## 🔧 Service Management

### Start/Stop Service
```bash
# Start
systemctl start telegram-checker

# Stop
systemctl stop telegram-checker

# Restart
systemctl restart telegram-checker

# Status
systemctl status telegram-checker
```

### View Logs
```bash
# Real-time logs
journalctl -u telegram-checker -f

# Recent logs
journalctl -u telegram-checker -n 50

# Since boot
journalctl -u telegram-checker -b
```

### Enable Auto-start
```bash
# Enable service (starts on boot)
systemctl enable telegram-checker

# Disable service
systemctl disable telegram-checker
```

## 🔐 Security & Sessions

### Session Management
- **Session files** are stored as `telegram_checker_session.session`
- **Automatic reconnection** on service restart
- **Persistent authorization** after first setup

### When to Re-authenticate
You need to manually re-authenticate when:
- **Changing Telegram password**
- **Updating 2FA settings**
- **Modifying API credentials**
- **Session expires** (rare, usually months)

### Re-authentication Process
```bash
# 1. Stop service
systemctl stop telegram-checker

# 2. Start manually
source venv/bin/activate
python flask_api_fast.py

# 3. Enter new verification code

# 4. Stop (Ctrl+C)

# 5. Restart service
systemctl start telegram-checker
```

## 🚨 Troubleshooting

### Service Won't Start
```bash
# Check logs
journalctl -u telegram-checker -n 20

# Common issues:
# - Port 5000 already in use
# - Missing session file
# - Invalid credentials
```

### API Not Responding
```bash
# Check if service is running
systemctl status telegram-checker

# Test health endpoint
curl http://localhost:5000/health

# Check Telegram connection
curl http://localhost:5000/health | jq '.telegram_connected'
```

### FloodWait Errors
- Service automatically handles FloodWait
- Delays are adaptive and random
- No manual intervention needed

### Port Conflicts
```bash
# Check what's using port 5000
lsof -i :5000

# Kill conflicting process
kill <PID>

# Restart service
systemctl restart telegram-checker
```

## 📈 Performance

### Rate Limits
- **Phone numbers**: ~30-50 per hour per account
- **Usernames**: ~100-200 per hour per account
- **Adaptive delays**: 2-8 seconds between requests

### Batch Processing
- **Recommended batch size**: 1-5 items per request
- **Timeout**: 60 seconds per request
- **Concurrent processing**: Single-threaded with async

### Scaling
For high-volume processing, consider:
- **Multiple bot accounts** (requires code modification)
- **Load balancing** across multiple instances
- **Queue-based processing** for large datasets

## 🔄 Integration Examples

### n8n Workflow
```javascript
// HTTP Request node
{
  "method": "POST",
  "url": "http://your-server:5000/check_phones",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "phones": ["+1234567890"]
  },
  "timeout": 60000
}
```

### Python Client
```python
import requests

def check_phone(phone):
    response = requests.post(
        'http://localhost:5000/check_phones',
        json={'phones': [phone]},
        timeout=60
    )
    return response.json()

# Usage
result = check_phone('+1234567890')
print(result)
```

### cURL Examples
```bash
# Check single phone
curl -X POST http://localhost:5000/check_phones \
  -H "Content-Type: application/json" \
  -d '{"phones": ["+1234567890"]}'

# Check multiple usernames
curl -X POST http://localhost:5000/check_usernames \
  -H "Content-Type: application/json" \
  -d '{"usernames": ["user1", "user2", "user3"]}'

# Health check
curl http://localhost:5000/health
```

## 📝 License

MIT License - Use responsibly and respect Telegram's terms of service.

## ⚠️ Important Notes

- **Educational use only** - Respect user privacy
- **Rate limiting** - Don't abuse Telegram's API
- **Session security** - Keep session files secure
- **Regular updates** - Keep dependencies updated
- **Monitoring** - Monitor logs for issues

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

---

**Happy checking! 🎯**
