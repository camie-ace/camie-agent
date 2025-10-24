"""
Utility to extract phone numbers from room names and fetch configuration from API
"""

import os
import re
import jwt
import json
from typing import Dict, Any, Optional, Tuple
from utils.api_client import APIClient


async def extract_phone_from_room_name(room_name: str) -> Optional[str]:
    """
    Extract a phone number from a LiveKit room name

    Args:
        room_name: The LiveKit room name (format: "twilio-+12345678901-XXXXX")

    Returns:
        Extracted phone number or None if not found
    """
    if not room_name:
        return None

    # Pattern to match phone numbers in format: twilio-+12345678901-XXXXX
    pattern = r'twilio-(\+?\d+)-'
    match = re.search(pattern, room_name)

    if match:
        return match.group(1)
    return None


async def create_phone_jwt(phone_number: str, direction: str, room_name: str) -> str:
    """
    Create a JWT token for the phone number using environment variables

    Args:
        phone_number: The phone number to encode in the JWT

    Returns:
        JWT token string
    """
    jwt_secret = os.getenv("JWT_SECRET")
    jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")

    if not jwt_secret:
        raise ValueError("JWT_SECRET not configured in environment variables")

    payload = {"phone_number": phone_number,
               direction: direction, "room_name": room_name}
    token = jwt.encode(payload, jwt_secret, algorithm=jwt_algorithm)

    # Handle PyJWT's different return types (bytes in older versions, str in newer versions)
    if isinstance(token, bytes):
        token = token.decode('utf-8')

    return token


async def fetch_agent_config_by_phone(phone_number: str, call_direction: Optional[str] = None, room_name: Optional[str] = None) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Fetch agent configuration from API using phone number

    Args:
        phone_number: The phone number to get configuration for
        call_direction: The call direction ("inbound" or "outbound") if known
        room_name: Optional room name for the call

    Returns:
        Tuple of (agent_config, extracted_direction) where extracted_direction is from the API response
        if call_direction wasn't provided
    """
    token = await create_phone_jwt(phone_number, call_direction, room_name)
    config_url = os.getenv("VOICE_CONFIG_TOKEN_URL")

    if not config_url:
        raise ValueError(
            "VOICE_CONFIG_TOKEN_URL not configured in environment variables")

    async with APIClient() as client:
        headers = {"Authorization": f"Bearer {token}"}
        params = {}
        if call_direction:
            params["direction"] = call_direction
        if room_name:
            params["room_name"] = room_name

        # Only pass params if we have any
        params = params if params else None

        print(
            f"Fetching agent config for phone: {phone_number}, direction: {call_direction or 'inbound'}, room: {room_name or 'n/a'}")
        result = await client._make_request("GET", config_url, headers=headers, params=params)

        if result.get("error") or result.get("responseCode") != "00":
            error_message = result.get("message") or result.get(
                "description") or "Unknown error"
            print(f"Error fetching configuration: {error_message}")
            return {}, None

        # Extract the phone config from the data field containing the phone number object
        data = result.get("data", {})

        # Look for the phone number in the data
        # The phone number might be with or without a plus, so check both formats
        phone_config = data.get(phone_number, None)
        if phone_config is None and phone_number.startswith('+'):
            # Try without the plus
            phone_config = data.get(phone_number[1:], None)
        if phone_config is None and not phone_number.startswith('+'):
            # Try with the plus
            phone_config = data.get(f"+{phone_number}", None)

        if not phone_config:
            print(f"No configuration found for phone number: {phone_number}")
            return {}, None

        # If call_direction is provided, use it to get the specific config
        if call_direction and call_direction in phone_config:
            return phone_config[call_direction], call_direction

        # If not provided, try to determine from available keys
        if "inbound" in phone_config:
            return phone_config["inbound"], "inbound"
        elif "outbound" in phone_config:
            return phone_config["outbound"], "outbound"

        # If we can't determine, return the whole phone_config
        return phone_config, None


async def get_agent_config_from_room(room_name: str, participant_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Get agent configuration from room name and participant metadata

    Args:
        room_name: The LiveKit room name
        participant_metadata: Optional metadata with call direction

    Returns:
        Agent configuration dictionary
    """
    phone_number = await extract_phone_from_room_name(room_name)

    if not phone_number:
        print(f"Could not extract phone number from room name: {room_name}")
        return {}

    # Extract call direction from metadata if available
    call_direction = None
    if participant_metadata and isinstance(participant_metadata, dict):
        call_direction = participant_metadata.get("direction")
        if call_direction:
            print(f"Using call direction from metadata: {call_direction}")
        else:
            print("No call direction found in metadata, defaulting to inbound")
            call_direction = "inbound"

    try:
        config, detected_direction = await fetch_agent_config_by_phone(phone_number, call_direction, room_name)

        if not config:
            print(
                f"No configuration found for phone: {phone_number}, direction: {call_direction}")
            return {}

        if detected_direction and call_direction and detected_direction != call_direction:
            print(
                f"Warning: Detected direction ({detected_direction}) differs from metadata direction ({call_direction})")

        # Log the configuration keys we've received to help with debugging
        config_keys = list(config.keys())
        print(f"Received configuration with keys: {config_keys}")

        return config
    except Exception as e:
        print(f"Error getting agent config: {e}")
        return {}
