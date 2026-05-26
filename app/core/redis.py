import redis
import redis.asyncio as aioredis

from app.core.config import settings

redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)


def get_redis_client() -> redis.Redis:
    return redis.Redis(connection_pool=redis_pool)


async def get_async_redis():
    client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()
