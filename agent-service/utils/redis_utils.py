"""
Stub implementation of Redis utilities

This module provides non-functional stubs for Redis-related functions.
These stubs allow the application to run without an actual Redis dependency.
"""

import os

# No actual Redis import
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_pool = None


async def get_redis_pool_instance():
    """
    Stub for initializing a Redis connection pool.
    Raises NotImplementedError to prevent actual use.
    """
    print("WARNING: Redis functionality is disabled. Using stub implementation.")
    return None


async def get_redis_connection():
    """
    Stub for getting a Redis connection.
    Raises NotImplementedError to prevent actual use.
    """
    print("WARNING: Redis functionality is disabled. Using stub implementation.")

    class MockRedis:
        async def get(self, key):
            return None

        async def set(self, key, value, ex=None):
            return None

        async def delete(self, key):
            return None

    return MockRedis()


async def close_redis_pool():
    """
    Stub for closing a Redis connection pool.
    Does nothing since there's no actual pool.
    """
    print("WARNING: Redis functionality is disabled. Using stub implementation.")
    return None
