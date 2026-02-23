# Redis Cache Usage Guide

This guide demonstrates how to use Redis caching in your FastAPI application.

## Overview

The Redis cache is **automatically enabled in production** (when `DEBUG=False`) and **disabled in development** (when `DEBUG=True`). This ensures that developers can work without Redis during development while production benefits from caching.

## Configuration

Add these settings to your `.env` file for production:

```bash
DEBUG=False
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_redis_password  # Optional
REDIS_MAX_CONNECTIONS=10
```

## Usage Examples

### 1. Using the Cache Dependency

```python
from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from src.apps.core.dependencies import get_redis_cache

router = APIRouter()

@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    cache: Redis = Depends(get_redis_cache)
):
    """
    The cache parameter will be:
    - None in development (DEBUG=True)
    - Redis client in production (DEBUG=False)
    """
    
    # Try to get from cache first (production only)
    if cache:
        cached_user = await cache.get(f"user:{user_id}")
        if cached_user:
            return json.loads(cached_user)
    
    # Fetch from database
    user = await fetch_user_from_db(user_id)
    
    # Cache the result (production only)
    if cache:
        await cache.setex(
            f"user:{user_id}",
            3600,  # TTL: 1 hour
            json.dumps(user)
        )
    
    return user
```

### 2. Using the RedisCache Helper Class

```python
from fastapi import APIRouter
from src.apps.core.cache import RedisCache

router = APIRouter()

@router.get("/products/{product_id}")
async def get_product(product_id: int):
    """Using RedisCache helper class for cleaner code"""
    
    cache_key = f"product:{product_id}"
    
    # Try cache (automatically skipped in development)
    cached = await RedisCache.get(cache_key)
    if cached:
        return cached
    
    # Fetch from database
    product = await fetch_product_from_db(product_id)
    
    # Cache the result with 30 minute TTL
    await RedisCache.set(cache_key, product, ttl=1800)
    
    return product
```

### 3. Using the Simple use_cache Dependency

```python
from fastapi import APIRouter, Depends
from src.apps.core.dependencies import use_cache
from src.apps.core.cache import RedisCache

router = APIRouter()

@router.get("/stats")
async def get_stats(should_cache: bool = Depends(use_cache)):
    """Simple boolean flag for cache logic"""
    
    if should_cache:
        cached_stats = await RedisCache.get("app:stats")
        if cached_stats:
            return cached_stats
    
    # Calculate stats
    stats = await calculate_stats()
    
    if should_cache:
        await RedisCache.set("app:stats", stats, ttl=300)  # 5 minutes
    
    return stats
```

### 4. Cache Invalidation

```python
from fastapi import APIRouter
from src.apps.core.cache import RedisCache

router = APIRouter()

@router.put("/users/{user_id}")
async def update_user(user_id: int, user_data: dict):
    """Update user and invalidate cache"""
    
    # Update in database
    user = await update_user_in_db(user_id, user_data)
    
    # Invalidate cache (automatically skipped in development)
    await RedisCache.delete(f"user:{user_id}")
    
    return user

@router.delete("/cache/users")
async def clear_user_cache():
    """Clear all user-related cache entries"""
    
    # Delete all keys matching pattern
    deleted_count = await RedisCache.clear_pattern("user:*")
    
    return {"message": f"Cleared {deleted_count} cache entries"}
```

### 5. Cache Wrapper Decorator (Advanced)

```python
from functools import wraps
from typing import Callable, Any
from src.apps.core.cache import RedisCache

def cached(key_prefix: str, ttl: int = 3600):
    """Decorator to cache function results"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Create cache key from function args
            cache_key = f"{key_prefix}:{':'.join(map(str, args))}"
            
            # Try cache
            cached_result = await RedisCache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            await RedisCache.set(cache_key, result, ttl=ttl)
            
            return result
        return wrapper
    return decorator

# Usage
@cached(key_prefix="user_profile", ttl=1800)
async def get_user_profile(user_id: int):
    """This function's results will be cached automatically"""
    return await fetch_user_profile_from_db(user_id)
```

## Cache Patterns

### Pattern 1: Cache-Aside (Lazy Loading)

```python
async def get_data(key: str):
    # Check cache
    data = await RedisCache.get(key)
    if data:
        return data
    
    # Load from source
    data = await load_from_source(key)
    
    # Store in cache
    await RedisCache.set(key, data, ttl=3600)
    
    return data
```

### Pattern 2: Write-Through

```python
async def save_data(key: str, data: dict):
    # Save to database
    await save_to_database(key, data)
    
    # Update cache immediately
    await RedisCache.set(key, data, ttl=3600)
```

### Pattern 3: Cache Warming

```python
async def warm_cache():
    """Pre-populate cache with frequently accessed data"""
    if not settings.DEBUG:
        popular_items = await get_popular_items()
        for item in popular_items:
            await RedisCache.set(
                f"item:{item.id}",
                item.dict(),
                ttl=7200
            )
```

## Best Practices

1. **Always set appropriate TTL**: Don't let cache entries live forever
2. **Use meaningful key prefixes**: Makes it easier to invalidate related entries
3. **Handle cache failures gracefully**: Cache should enhance performance, not break functionality
4. **Monitor cache hit rates**: Track how effective your caching strategy is
5. **Cache serializable data**: Use JSON-serializable objects or convert to dict first

## Testing

In tests, you can control the cache behavior by setting `DEBUG=True` or `DEBUG=False`:

```python
def test_with_cache(monkeypatch):
    """Test with cache enabled"""
    monkeypatch.setattr("src.apps.core.config.settings.DEBUG", False)
    # Your test code here

def test_without_cache():
    """Test without cache (default in test environment)"""
    # Cache will be automatically disabled if DEBUG=True
    pass
```

## Monitoring

Check if cache is available:

```python
from src.apps.core.cache import RedisCache

async def health_check():
    client = await RedisCache.get_client()
    if client:
        try:
            await client.ping()
            return {"cache": "healthy"}
        except Exception as e:
            return {"cache": "unhealthy", "error": str(e)}
    return {"cache": "disabled"}
```
