# Celery Background Tasks Setup

This project uses Celery for handling background tasks, primarily for email sending operations.

## Configuration

### Development Environment
- In development (`DEBUG=True`), Celery uses **in-memory broker** (`memory://`) and **in-memory result backend** (`cache+memory://`)
- No Redis installation required for development
- Celery worker runs in the same process space with minimal setup

### Production Environment
- In production (`DEBUG=False`), Celery uses **Redis** as both broker and result backend
- Redis must be installed and running
- Configuration automatically switches based on the `DEBUG` environment variable

## Environment Variables

### Redis Settings (Production only)
```env
DEBUG=False
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### Email Settings
```env
EMAIL_ENABLED=True
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=user@example.com
EMAIL_HOST_PASSWORD=your_password
EMAIL_FROM_ADDRESS=noreply@example.com
```

## Running Celery

### Development
```bash
# Start the Celery worker
task celery
# or
celery -A src.apps.core.celery_app worker --loglevel=info
```

### Production
1. Install and start Redis:
```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis-server

# macOS
brew install redis
brew services start redis

# Docker
docker run -d -p 6379:6379 redis:alpine
```

2. Set environment variable:
```bash
export DEBUG=False
```

3. Start the Celery worker:
```bash
task celery
# or
celery -A src.apps.core.celery_app worker --loglevel=info
```

## Background Tasks

The following email operations are handled asynchronously via Celery:

1. **Welcome Email** - Sent when a new user registers
2. **Password Reset Email** - Sent when user requests password reset
3. **Email Verification** - Sent for email address verification
4. **New IP Notification** - Sent when login from new IP address is detected

## Usage

The email service automatically queues tasks to Celery:

```python
from src.apps.iam.services.email import EmailService

# This will queue the email task in background
await EmailService.send_welcome_email(user)
```

## Monitoring

To monitor Celery tasks in production, you can use Flower:

```bash
pip install flower
celery -A src.apps.core.celery_app flower
```

Access the web interface at `http://localhost:5555`

## Architecture

```
FastAPI App
    ↓
EmailService (queues tasks)
    ↓
Celery Tasks (background execution)
    ↓
FastAPI-Mail (actual email sending)
```

## Benefits

- **Non-blocking**: Email sending doesn't block the API response
- **Reliable**: Failed tasks can be retried automatically
- **Scalable**: Multiple workers can process tasks in parallel
- **Production-ready**: Redis provides persistence and reliability
- **Development-friendly**: Memory backend requires no additional services
