# Celery Quick Start Guide

## Installation Complete ✓

Celery has been successfully integrated with your FastAPI application!

## What You Get

- **Background email processing** using Celery
- **Development mode**: In-memory broker (no Redis needed)
- **Production mode**: Redis-backed broker (reliable & scalable)
- **Automatic switching** based on DEBUG environment variable

## Usage

### Start the Application

**Terminal 1 - Start Celery Worker:**
```bash
task celery
```

**Terminal 2 - Start FastAPI:**
```bash
task start
```

### How It Works

When you call any email method, it now runs in the background:

```python
await EmailService.send_welcome_email(user)  # Returns immediately!
```

The email is queued to Celery and sent asynchronously by the worker.

## Environment Modes

### Development (DEFAULT)
```bash
DEBUG=True  # in your .env file
```
- Uses in-memory broker
- No Redis installation needed
- Perfect for local development
- Run: `task celery` and `task start`

### Production
```bash
DEBUG=False  # in your .env file
```
- Uses Redis broker
- Install Redis first: `brew install redis` (macOS) or `apt install redis-server` (Linux)
- Start Redis: `brew services start redis` or `systemctl start redis-server`
- Run: `task celery` and `task start`

## Verify Setup

Run the verification script:
```bash
python test_celery_setup.py
```

## Background Tasks Available

1. ✉️ Welcome emails (on signup)
2. 🔑 Password reset emails
3. ✅ Email verification
4. 🌐 New IP address notifications

All of these run in the background without blocking your API!

## Need Help?

- Full setup guide: [CELERY_SETUP.md](CELERY_SETUP.md)
- Implementation details: [CELERY_IMPLEMENTATION.md](CELERY_IMPLEMENTATION.md)

## Testing

Tests automatically mock email services and disable rate limiting. Run:
```bash
task test
```

---

**That's it! Your background task processing is ready to use! 🎉**
