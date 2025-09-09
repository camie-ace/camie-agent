"""
Mock Redis utilities module

This module provides dummy functions to replace Redis integration.
All Redis caching has been removed from the codebase.
"""


async def get_redis_connection():
    """Dummy function to replace Redis connection"""
    raise NotImplementedError("Redis connection is not available")


async def close_redis_pool():
    """Dummy function to close Redis connection pool"""
    pass
