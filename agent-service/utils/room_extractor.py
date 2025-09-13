"""
Utility functions for extracting room names and phone numbers from various sources
"""

import logging
import re

# Configure logging
logger = logging.getLogger(__name__)


def extract_room_name(ctx):
    """
    Extract room name from a job context using multiple fallback methods

    Args:
        ctx: The JobContext object

    Returns:
        str: The extracted room name or "unknown" if extraction fails
    """
    # Primary method: Try to access through the standard API
    try:
        if hasattr(ctx, 'job') and hasattr(ctx.job, 'request') and hasattr(ctx.job.request, 'room_name'):
            return ctx.job.request.room_name
    except AttributeError:
        logger.debug("Could not access room_name through standard API")

    # Fallback 1: Try to access through the context's string representation
    try:
        ctx_str = str(ctx)
        if "room_name=" in ctx_str:
            # Handle various patterns with better regex
            import re
            match = re.search(r'room_name=([^,)]+)', ctx_str)
            if match:
                room_name = match.group(1).strip()
                if room_name and room_name != "None":
                    return room_name
    except Exception as e:
        logger.debug(f"Error extracting room name from context string: {e}")

    # Fallback 2: Try to extract from the job's string representation
    try:
        if hasattr(ctx, 'job'):
            job_str = str(ctx.job)
            if "room_name=" in job_str:
                room_name = job_str.split("room_name=")[
                    1].split(",")[0].strip()
                if room_name and room_name != "None":
                    return room_name
    except Exception as e:
        logger.debug(f"Error extracting room name from job string: {e}")

    # Fallback 3: Try to extract from job ID or other available info
    try:
        if hasattr(ctx, 'job') and hasattr(ctx.job, 'id'):
            job_id = ctx.job.id
            # Log the job ID for debugging
            logger.debug(f"Job ID: {job_id}")
            # This is where you might call an external service if needed
    except Exception as e:
        logger.debug(f"Error accessing job ID: {e}")

    # Last resort: Check if the context object has any attributes that might contain the room name
    try:
        if hasattr(ctx, 'room') and ctx.room is not None:
            room_name = ctx.room.name
            if room_name and room_name != "None":
                return room_name
    except Exception as e:
        logger.debug(f"Error accessing room name from room object: {e}")

    # If all methods fail, return unknown
    return "unknown"


def extract_phone_number(room_name):
    """
    Extract phone number from a room name

    Args:
        room_name: The room name string, typically in format 'twilio-+PHONENUMBER-UUID'

    Returns:
        str: The extracted phone number or None if extraction fails
    """
    if not room_name or room_name == "unknown":
        return None

    # Try to extract using regex patterns
    # Pattern 1: For Twilio format "twilio-+NUMBER-UUID"
    twilio_pattern = r'twilio-\+?([0-9]+)-'
    match = re.search(twilio_pattern, room_name)
    if match:
        return "+" + match.group(1)

    # Pattern 2: Direct phone number in the string
    phone_pattern = r'\+([0-9]+)'
    match = re.search(phone_pattern, room_name)
    if match:
        return "+" + match.group(1)

    # Pattern 3: Look for numbers of typical phone length (7-15 digits)
    numbers_pattern = r'[0-9]{7,15}'
    match = re.search(numbers_pattern, room_name)
    if match:
        number = match.group(0)
        # Add + prefix if it looks like an international number
        return "+" + number if len(number) > 9 else number

    return None
