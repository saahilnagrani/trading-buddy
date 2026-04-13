import redis.asyncio as redis

from app.config import settings

redis_pool = redis.ConnectionPool.from_url(
    settings.redis_url,
    decode_responses=True,
    max_connections=5,
    socket_connect_timeout=5,
    socket_timeout=5,
    retry_on_timeout=True,
)

# Single shared Redis client (reuses connections from pool)
_redis_client = redis.Redis(connection_pool=redis_pool)


def get_redis() -> redis.Redis:
    return _redis_client
