import asyncio
import json
from typing import Dict, Any

from utils.redis_utils import get_redis_connection  # Relative import
from .config_definitions import DEFAULT_SETTINGS  # Relative import

# Placeholder for fetching settings from the actual user accounts microservice


async def fetch_settings_from_microservice(user_id: str) -> Dict[str, Any]:
    """
    Simulates fetching settings for a user_id from an external microservice.
    Replace this with your actual HTTP client call.
    """
    print(
        f"Simulating fetching settings for user_id: {user_id} from microservice...")
    await asyncio.sleep(0.1)  # Simulate network delay
    # In a real scenario, you might fetch and merge with a base set of defaults
    # or the microservice returns a complete settings object.
    # For this simulation, we just return a copy of the application's default settings.
    return DEFAULT_SETTINGS.copy()


async def get_user_settings(user_id: str) -> Dict[str, Any]:
    """
    Retrieves user settings, trying cache first, then fetching from microservice.
    """
    if not user_id:
        print("No user_id provided, using default application settings.")
        return DEFAULT_SETTINGS.copy()

    r = await get_redis_connection()
    cache_key = f"user_settings:{user_id}"

    try:
        cached_settings_json = await r.get(cache_key)
        if cached_settings_json:
            print(f"Cache hit for user_id: {user_id}")
            return json.loads(cached_settings_json)
    except Exception as e:
        # Log the error but proceed to fetch, as cache is not critical for operation if fetch works
        print(f"Redis GET error for user_id {user_id}: {e}")

    print(f"Cache miss for user_id: {user_id}. Fetching from microservice.")
    settings = await fetch_settings_from_microservice(user_id)

    try:
        # Cache for 1 hour
        await r.set(cache_key, json.dumps(settings), ex=3600)
    except Exception as e:
        # Log the error; failing to cache is not critical for the current operation
        print(f"Redis SET error for user_id {user_id}: {e}")

    return settings
