# Redis Cache Implementation for Production

This document provides a comprehensive guide to the Redis caching implementation in this FastAPI application.

## Overview

The Redis cache is **environment-aware**:
- **Development** (`DEBUG=True`): Cache is disabled, all operations return None/False
- **Production** (`DEBUG=False`): Redis cache is fully enabled and operational

This approach allows seamless development without requiring Redis while maintaining performance benefits in production.

## Installation & Setup

### 1. Redis is already included in dependencies

The `pyproject.toml` already includes `redis>=5.2.0` in the dependencies.

### 2. Environment Configuration

Update your `.env` file for production:

```bash
# Set to False to enable Redis cache
DEBUG=False

# Redis connection settings
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_password  # Optional, only if Redis requires auth
REDIS_MAX_CONNECTIONS=10
```

For development, keep:
```bash
DEBUG=True
```

### 3. Start Redis Server

**Using Docker:**
```bash
docker run -d --name redis -p 6379:6379 redis:latest
```

**Using Docker with password:**
```bash
docker run -d --name redis -p 6379:6379 redis:latest --requirepass your_password
```

**Using Homebrew (macOS):**
```bash
brew install redis
brew services start redis
```

**Using apt (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
```

### 4. Verify Redis Connection

```bash
redis-cli ping
# Should return: PONG
```

## File Structure

```
src/apps/core/
├── cache.py           # RedisCache class with cache operations
├── dependencies.py    # FastAPI dependencies for caching
└── config.py          # Redis configuration settings

tests/
└── test_redis_cache.py  # Comprehensive test suite

src/apps/examples/
└── cache_endpoints.py   # Example endpoints showing cache usage
```

## Core Components

### 1. RedisCache Class (`src/apps/core/cache.py`)

Singleton-style class providing cache operations:

```python
from src.apps.core.cache import RedisCache

# Get value
data = await RedisCache.get("key")

# Set value with TTL
await RedisCache.set("key", {"data": "value"}, ttl=3600)

# Delete key
await RedisCache.delete("key")

# Check if key exists
exists = await RedisCache.exists("key")

# Clear keys by pattern
count = await RedisCache.clear_pattern("user:*")

# Close connection (handled automatically on shutdown)
await RedisCache.close()
```

### 2. FastAPI Dependencies (`src/apps/core/dependencies.py`)

#### `get_redis_cache()` - Returns Redis client or None

```python
from fastapi import Depends
from redis.asyncio import Redis
from src.apps.core.dependencies import get_redis_cache

@router.get("/endpoint")
async def endpoint(cache: Redis = Depends(get_redis_cache)):
    if cache:
        # Use cache in production
        data = await cache.get("key")
    else:
        # Skip cache in development
        pass
```

#### `use_cache()` - Returns boolean flag

```python
from fastapi import Depends
from src.apps.core.dependencies import use_cache

@router.get("/endpoint")
async def endpoint(should_cache: bool = Depends(use_cache)):
    if should_cache:
        # Cache logic here
        pass
```

## Usage Patterns

### Pattern 1: Cache-Aside (Lazy Loading)

Most common pattern - check cache first, then database:

```python
from src.apps.core.cache import RedisCache

@router.get("/users/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    cache_key = f"user:{user_id}"
    
    # Try cache
    cached = await RedisCache.get(cache_key)
    if cached:
        return cached
    
    # Fetch from database
    user = await fetch_user(db, user_id)
    
    # Store in cache (1 hour TTL)
    await RedisCache.set(cache_key, user, ttl=3600)
    
    return user
```

### Pattern 2: Write-Through

Update cache immediately when data changes:

```python
@router.put("/users/{user_id}")
async def update_user(user_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    # Update database
    user = await update_user_in_db(db, user_id, data)
    
    # Update cache immediately
    await RedisCache.set(f"user:{user_id}", user, ttl=3600)
    
    return user
```

### Pattern 3: Cache Invalidation

Remove stale data when changes occur:

```python
@router.delete("/users/{user_id}")
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    # Delete from database
    await delete_user_from_db(db, user_id)
    
    # Invalidate cache
    await RedisCache.delete(f"user:{user_id}")
    
    # Also clear related caches
    await RedisCache.clear_pattern(f"users:list:*")
    
    return {"message": "User deleted"}
```

### Pattern 4: Cache Warming

Pre-populate cache with frequently accessed data:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await warm_cache()
    yield
    # Shutdown
    await RedisCache.close()

async def warm_cache():
    if not settings.DEBUG:
        # Cache popular items
        items = await get_popular_items()
        for item in items:
            await RedisCache.set(f"item:{item.id}", item, ttl=3600)
```

## Lifecycle Management

The Redis connection is automatically managed in `src/main.py`:

```python
from src.apps.core.cache import RedisCache

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Redis in production
    if not settings.DEBUG:
        await RedisCache.get_client()
    
    yield
    
    # Cleanup Redis connection
    await RedisCache.close()
```

## Testing

Run the test suite:

```bash
pytest tests/test_redis_cache.py -v
```

The tests verify:
- ✅ Cache is disabled in DEBUG mode
- ✅ Cache is enabled in production mode
- ✅ All cache operations work correctly
- ✅ Error handling for Redis failures
- ✅ JSON serialization/deserialization
- ✅ Connection cleanup

## Example Endpoints

Example cache endpoints are provided in `src/apps/examples/cache_endpoints.py`:

1. **User Profile with Cache** - `/examples/users/{user_id}/profile`
2. **List Users with Cache** - `/examples/users/list`
3. **Dashboard Stats with Cache** - `/examples/stats/dashboard`
4. **Update Profile (with invalidation)** - `/examples/users/{user_id}/profile`
5. **Cache Health Check** - `/examples/cache/health`
6. **Clear Cache (admin)** - `/examples/cache/clear`
7. **Cache Info (admin)** - `/examples/cache/info`

To use these examples, add the router to your main application:

```python
from src.apps.examples.cache_endpoints import router as examples_router

app.include_router(examples_router, prefix=settings.API_V1_STR)
```

## Monitoring & Health Checks

### Health Check Endpoint

```python
@router.get("/health/cache")
async def cache_health():
    if not settings.DEBUG:
        try:
            client = await RedisCache.get_client()
            await client.ping()
            return {"status": "healthy"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    return {"status": "disabled"}
```

### Get Cache Statistics

```python
from redis.asyncio import Redis
from src.apps.core.dependencies import get_redis_cache

@router.get("/admin/cache/stats")
async def cache_stats(cache: Redis = Depends(get_redis_cache)):
    if cache:
        info = await cache.info()
        return {
            "used_memory": info.get("used_memory_human"),
            "connected_clients": info.get("connected_clients"),
            "total_commands": info.get("total_commands_processed"),
        }
    return {"message": "Cache disabled"}
```

## Best Practices

### 1. Use Appropriate TTL Values

```python
# Short-lived data (5 minutes)
await RedisCache.set("temp:data", value, ttl=300)

# Medium-lived data (1 hour)
await RedisCache.set("user:profile", value, ttl=3600)

# Long-lived data (24 hours)
await RedisCache.set("config:settings", value, ttl=86400)
```

### 2. Use Meaningful Key Prefixes

```python
# Good - organized by domain
user:123:profile
user:123:settings
order:456:details
stats:dashboard:daily

# Bad - hard to manage
user123
data456
temp789
```

### 3. Handle Cache Failures Gracefully

```python
try:
    cached = await RedisCache.get(key)
    if cached:
        return cached
except Exception as e:
    # Log error but continue
    logger.error(f"Cache error: {e}")

# Always fall back to database
return await fetch_from_database()
```

### 4. Invalidate Related Caches

```python
# When updating a user
await RedisCache.delete(f"user:{user_id}")
await RedisCache.clear_pattern("users:list:*")
await RedisCache.clear_pattern(f"user:{user_id}:*")
```

### 5. Cache Serializable Data Only

```python
# Good - dict is JSON serializable
user_data = {"id": 1, "name": "John"}
await RedisCache.set("user:1", user_data)

# Good - convert Pydantic model to dict
await RedisCache.set("user:1", user_model.dict())

# Bad - custom objects may not serialize
await RedisCache.set("user:1", user_object)  # May fail
```

## Troubleshooting

### Cache Not Working

1. **Check DEBUG setting:**
   ```bash
   # In your .env file
   DEBUG=False  # Must be False for cache to work
   ```

2. **Verify Redis is running:**
   ```bash
   redis-cli ping
   ```

3. **Check Redis connection:**
   ```python
   from src.apps.core.cache import RedisCache
   client = await RedisCache.get_client()
   print(client)  # Should not be None
   ```

### Connection Errors

1. **Check Redis password:**
   ```bash
   # In .env
   REDIS_PASSWORD=your_password
   ```

2. **Verify Redis host/port:**
   ```bash
   redis-cli -h localhost -p 6379 ping
   ```

3. **Check Redis logs:**
   ```bash
   # Docker
   docker logs redis
   
   # System service
   sudo journalctl -u redis
   ```

### Performance Issues

1. **Monitor memory usage:**
   ```bash
   redis-cli info memory
   ```

2. **Check slow queries:**
   ```bash
   redis-cli slowlog get 10
   ```

3. **Adjust max connections:**
   ```bash
   # In .env
   REDIS_MAX_CONNECTIONS=20
   ```

## Production Deployment

### Docker Compose Example

```yaml
services:
  api:
    build: .
    environment:
      - DEBUG=False
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    depends_on:
      - redis
  
  redis:
    image: redis:latest
    command: redis-server --requirepass ${REDIS_PASSWORD}
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

### Environment Variables

```bash
# Production .env
DEBUG=False
REDIS_HOST=redis  # Docker service name
REDIS_PORT=6379
REDIS_PASSWORD=strong_password_here
REDIS_MAX_CONNECTIONS=20
```

## Summary

- ✅ Redis cache automatically enabled in production (`DEBUG=False`)
- ✅ No Redis required for development (`DEBUG=True`)
- ✅ Simple dependencies: `get_redis_cache()` and `use_cache()`
- ✅ Helper class `RedisCache` for clean code
- ✅ Comprehensive test coverage
- ✅ Example endpoints demonstrating patterns
- ✅ Automatic connection lifecycle management
- ✅ Graceful error handling
- ✅ Production-ready configuration

For more detailed examples, see `REDIS_CACHE_USAGE.md` and `src/apps/examples/cache_endpoints.py`.
