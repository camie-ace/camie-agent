import os
import redis.asyncio as redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_pool = None


async def get_redis_pool_instance():
    """
    Initializes and returns the global Redis connection pool.
    Ensures only one pool is created.
    """
    global redis_pool
    if redis_pool is None:
        print("Initializing Redis connection pool...")
        redis_pool = redis.ConnectionPool.from_url(
            REDIS_URL, decode_responses=True)
    return redis_pool


async def get_redis_connection():
    """
    Returns a Redis connection from the global pool.
    """
    pool = await get_redis_pool_instance()
    return redis.Redis(connection_pool=pool)


async def close_redis_pool():
    """
    Closes the global Redis connection pool if it exists.
    """
    global redis_pool
    if redis_pool:
        print("Closing Redis connection pool...")
        await redis_pool.disconnect()  # For redis-py 4.2+
        # For older versions, it might be redis_pool.close() and then await redis_pool.wait_closed()
        redis_pool = None
