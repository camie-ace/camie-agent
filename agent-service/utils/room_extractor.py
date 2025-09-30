"""
Utility functions for extracting room names, phone numbers, and comprehensive 
SIP data from LiveKit room contexts and metadata.

Key functions:
- extract_room_name(): Basic room name extraction
- extract_phone_number(): Phone number extraction from room name
- extract_comp        # Pattern 2: "twilio-trunk-abc123-+1234567890" or "twilio-_3693_naxnFCNHxkDu"
        twilio_patterns = [
            r'twilio-trunk-([^-]+)-(.+)',  # Standard twilio-trunk-id-number
            r'twilio-_([^_]+)_(.+)',       # twilio-_id_identifier (like twilio-_3693_naxnFCNHxkDu)
            r'twilio-([^-_]+)-(.+)',       # twilio-id-identifier (generic dash separator)
            r'twilio-([^-_]+)_(.+)'        # twilio-id_identifier (generic underscore separator)
        ]
        
        for pattern in twilio_patterns:
            match = re.search(pattern, room_name, re.IGNORECASE)
            if match:
                trunk_id, identifier = match.groups()
                sip_data["sip_trunk_id"] = trunk_id
                # For Twilio patterns, the identifier might be the call ID or session ID
                sip_data["call_id"] = identifier
                logger.debug(f"Extracted Twilio SIP data: trunk_id={trunk_id}, call_id={identifier}")
                breakve_room_data(): Complete SIP and room data extraction
- log_all_available_data(): Debug function for exploring available data
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


def extract_comprehensive_room_data(ctx):
    """
    Extract comprehensive room data including SIP information and metadata

    Args:
        ctx: The JobContext object

    Returns:
        dict: Dictionary containing all available room and SIP data
    """
    room_data = {
        "room_name": "unknown",
        "sip_from": None,
        "sip_to": None,
        "sip_trunk_id": None,
        "call_id": None,
        "direction": None,
        "participant_metadata": {},
        "room_metadata": {},
        "job_id": None,
        "additional_attributes": {}
    }

    try:
        # Extract basic room name
        room_data["room_name"] = extract_room_name(ctx)

        # Extract job ID if available
        if hasattr(ctx, 'job') and hasattr(ctx.job, 'id'):
            room_data["job_id"] = ctx.job.id
            logger.debug(f"Job ID: {ctx.job.id}")

        # Extract room-level data
        if hasattr(ctx, 'room') and ctx.room is not None:
            # Room metadata
            if hasattr(ctx.room, 'metadata') and ctx.room.metadata:
                try:
                    import json
                    if isinstance(ctx.room.metadata, str):
                        room_data["room_metadata"] = json.loads(
                            ctx.room.metadata)
                    else:
                        room_data["room_metadata"] = ctx.room.metadata
                except (json.JSONDecodeError, AttributeError) as e:
                    logger.debug(f"Could not parse room metadata: {e}")
                    room_data["room_metadata"] = {
                        "raw": str(ctx.room.metadata)}

            # Extract participant metadata (this often contains SIP data)
            if hasattr(ctx.room, 'local_participant') and ctx.room.local_participant:
                if hasattr(ctx.room.local_participant, 'metadata') and ctx.room.local_participant.metadata:
                    try:
                        import json
                        if isinstance(ctx.room.local_participant.metadata, str):
                            room_data["participant_metadata"] = json.loads(
                                ctx.room.local_participant.metadata)
                        else:
                            room_data["participant_metadata"] = ctx.room.local_participant.metadata
                    except (json.JSONDecodeError, AttributeError) as e:
                        logger.debug(
                            f"Could not parse participant metadata: {e}")
                        room_data["participant_metadata"] = {
                            "raw": str(ctx.room.local_participant.metadata)}

                # Extract SIP-related data from participant metadata
                if room_data["participant_metadata"]:
                    metadata = room_data["participant_metadata"]
                    room_data["sip_from"] = metadata.get("sip_from") or metadata.get(
                        "sipFrom") or metadata.get("from")
                    room_data["sip_to"] = metadata.get(
                        "sip_to") or metadata.get("sipTo") or metadata.get("to")
                    room_data["sip_trunk_id"] = metadata.get("sip_trunk_id") or metadata.get(
                        "sipTrunkId") or metadata.get("trunk_id")
                    room_data["call_id"] = metadata.get(
                        "call_id") or metadata.get("callId")
                    room_data["direction"] = metadata.get(
                        "direction") or metadata.get("call_direction")

            # Try to extract from room attributes (avoiding coroutines)
            room_attrs = dir(ctx.room)
            for attr in room_attrs:
                if attr.startswith('sip_') or attr in ['name', 'metadata']:
                    try:
                        value = getattr(ctx.room, attr)
                        # We already handled metadata
                        if value and attr not in ['metadata']:
                            room_data["additional_attributes"][attr] = str(
                                value)
                    except Exception as e:
                        logger.debug(
                            f"Could not access room attribute {attr}: {e}")

            # Handle sid separately since it's a coroutine
            try:
                # Don't try to access sid directly as it's async
                logger.debug("Skipping room.sid as it's a coroutine")
            except Exception as e:
                logger.debug(f"Error with room.sid: {e}")

        # Extract from job request if available
        if hasattr(ctx, 'job') and hasattr(ctx.job, 'request'):
            request = ctx.job.request
            request_attrs = dir(request)
            for attr in request_attrs:
                if attr.startswith('sip_') or attr in ['room_name', 'call_id']:
                    try:
                        value = getattr(request, attr)
                        if value:
                            room_data["additional_attributes"][f"request_{attr}"] = str(
                                value)
                    except Exception as e:
                        logger.debug(
                            f"Could not access request attribute {attr}: {e}")

        # Try to extract SIP data from room name patterns
        if room_data["room_name"] and room_data["room_name"] != "unknown":
            logger.debug(
                f"Attempting to extract SIP data from room name: {room_data['room_name']}")
            sip_data = extract_sip_data_from_room_name(room_data["room_name"])
            if sip_data:
                logger.debug(f"Extracted SIP data from room name: {sip_data}")
                # Only update if we don't already have these values
                for key, value in sip_data.items():
                    if not room_data.get(key) and value:
                        room_data[key] = value
                        logger.debug(
                            f"Set {key} = {value} from room name pattern")
            else:
                logger.debug("No SIP data found in room name patterns")

        # Fallback: Use environment variables if available
        if not room_data.get("sip_to") or not room_data.get("sip_from"):
            import os
            env_phone = os.getenv("PHONE_NUMBER")
            if env_phone:
                logger.debug(
                    f"Using environment PHONE_NUMBER as fallback: {env_phone}")
                # For inbound calls, this would typically be sip_to
                if not room_data.get("sip_to"):
                    room_data["sip_to"] = env_phone

    except Exception as e:
        logger.error(f"Error extracting comprehensive room data: {e}")

    return room_data


def extract_sip_data_from_room_name(room_name):
    """
    Extract SIP data from room name patterns

    Args:
        room_name: The room name string

    Returns:
        dict: Dictionary containing extracted SIP data
    """
    sip_data = {}

    if not room_name:
        return sip_data

    try:
        # Common SIP room name patterns
        # Pattern 1: "sip-trunk123-from+1234567890-to+0987654321"
        sip_pattern = r'sip-(?:trunk)?([^-]+)?-?from([^-]+)-to([^-]+)'
        match = re.search(sip_pattern, room_name, re.IGNORECASE)
        if match:
            trunk_id, sip_from, sip_to = match.groups()
            if trunk_id:
                sip_data["sip_trunk_id"] = trunk_id
            if sip_from:
                sip_data["sip_from"] = sip_from.replace(
                    '%2B', '+')  # URL decode +
            if sip_to:
                sip_data["sip_to"] = sip_to.replace('%2B', '+')

        # Pattern 2: "twilio-trunk-abc123-+1234567890"
        twilio_pattern = r'twilio-trunk-([^-]+)-(.+)'
        match = re.search(twilio_pattern, room_name, re.IGNORECASE)
        if match:
            trunk_id, number = match.groups()
            sip_data["sip_trunk_id"] = trunk_id
            sip_data["sip_from"] = number if number.startswith(
                '+') else f"+{number}"

        # Pattern 3: Look for trunk IDs in various formats
        trunk_patterns = [
            r'trunk[_-]?([a-zA-Z0-9]+)',
            r'trk[_-]?([a-zA-Z0-9]+)',
            r'sip[_-]?trunk[_-]?([a-zA-Z0-9]+)'
        ]

        for pattern in trunk_patterns:
            match = re.search(pattern, room_name, re.IGNORECASE)
            if match and not sip_data.get("sip_trunk_id"):
                sip_data["sip_trunk_id"] = match.group(1)
                break

    except Exception as e:
        logger.debug(f"Error extracting SIP data from room name: {e}")

    return sip_data


def log_all_available_data(ctx):
    """
    Debug function to log all available data in the context

    Args:
        ctx: The JobContext object
    """
    logger.info("=== COMPREHENSIVE ROOM DATA DEBUG ===")

    try:
        # Log context attributes
        ctx_attrs = [attr for attr in dir(ctx) if not attr.startswith('_')]
        logger.info(f"Context attributes: {ctx_attrs}")

        # Log job attributes
        if hasattr(ctx, 'job'):
            job_attrs = [attr for attr in dir(
                ctx.job) if not attr.startswith('_')]
            logger.info(f"Job attributes: {job_attrs}")

            if hasattr(ctx.job, 'request'):
                request_attrs = [attr for attr in dir(
                    ctx.job.request) if not attr.startswith('_')]
                logger.info(f"Job request attributes: {request_attrs}")

        # Log room attributes
        if hasattr(ctx, 'room') and ctx.room:
            room_attrs = [attr for attr in dir(
                ctx.room) if not attr.startswith('_')]
            logger.info(f"Room attributes: {room_attrs}")

            # Log participant attributes
            if hasattr(ctx.room, 'local_participant') and ctx.room.local_participant:
                participant_attrs = [attr for attr in dir(
                    ctx.room.local_participant) if not attr.startswith('_')]
                logger.info(
                    f"Local participant attributes: {participant_attrs}")

        # Extract and log comprehensive data
        comprehensive_data = extract_comprehensive_room_data(ctx)
        logger.info(f"Comprehensive room data: {comprehensive_data}")

    except Exception as e:
        logger.error(f"Error in debug logging: {e}")

    logger.info("=== END ROOM DATA DEBUG ===")
