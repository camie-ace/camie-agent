"""
Call History Test Utilities

This module provides test utilities for the call history functionality.
These functions are only used for testing and should not be used in production code.
"""

from utils.call_history import active_calls
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Reference to the call records in call_history.py


async def get_call_record(call_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a call record by ID (only from active calls)

    Args:
        call_id: The ID of the call to retrieve

    Returns:
        Dict or None: The call record if found, None otherwise
    """
    # Only check active calls - historical data is in the external API
    if call_id in active_calls:
        return active_calls[call_id].to_dict()

    # We don't have access to historical data anymore
    logger.warning(
        f"Call {call_id} not found in active calls and historical data not available")
    return None


async def get_calls_by_phone(phone_number: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get active call records for a specific phone number

    Note: Historical data is only available via the external API

    Args:
        phone_number: The phone number to retrieve calls for
        limit: Maximum number of records to return

    Returns:
        List: List of active call records
    """
    # Filter active calls by phone number
    matching_calls = [
        call.to_dict() for call in active_calls.values()
        if call.phone_number == phone_number
    ]

    logger.warning(
        "Historical call data is not available locally, only active calls are returned")
    return matching_calls[:limit]


async def get_recent_calls(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get active call records

    Note: Historical data is only available via the external API

    Args:
        limit: Maximum number of records to return

    Returns:
        List: List of active call records
    """
    # Return all active calls
    active_call_records = [call.to_dict() for call in active_calls.values()]

    logger.warning(
        "Historical call data is not available locally, only active calls are returned")
    return active_call_records[:limit]


async def get_call_statistics(start_date: Optional[str] = None,
                              end_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Get statistics on active calls

    Note: Historical data is only available via the external API

    Args:
        start_date: Start date for filtering (ISO format)
        end_date: End date for filtering (ISO format)

    Returns:
        Dict: Call statistics
    """
    logger.warning(
        "Historical call statistics are not available locally, only active calls are counted")

    # Only count active calls
    active_call_records = [call.to_dict() for call in active_calls.values()]

    # Calculate statistics
    total_calls = len(active_call_records)
    completed_calls = sum(
        1 for call in active_call_records if call.get('status') == 'completed')
    failed_calls = sum(
        1 for call in active_call_records if call.get('status') == 'failed')
    dropped_calls = sum(
        1 for call in active_call_records if call.get('status') == 'dropped')

    # Count calls by business type
    business_types = {}
    for call in active_call_records:
        business_type = call.get('agent_config', {}).get(
            'business_type', 'unknown')
        business_types[business_type] = business_types.get(
            business_type, 0) + 1

    # Count calls by language
    languages = {}
    for call in active_call_records:
        language = call.get('agent_config', {}).get('language', 'unknown')
        languages[language] = languages.get(language, 0) + 1

    return {
        "total_calls": total_calls,
        "completed_calls": completed_calls,
        "failed_calls": failed_calls,
        "dropped_calls": dropped_calls,
        "completion_rate": (completed_calls / total_calls if total_calls else 0),
        "calls_by_business_type": business_types,
        "calls_by_language": languages,
        "note": "Statistics are for active calls only. Historical data is stored in the external API."
    }


async def update_call_metrics(call_id: str, metrics: Dict[str, Any]) -> bool:
    """
    Update metrics for a call

    Args:
        call_id: The ID of the call to update
        metrics: The metrics to update

    Returns:
        bool: True if successful, False otherwise
    """
    # Check if call is in active calls
    if call_id not in active_calls:
        logger.warning(f"Call {call_id} not found in active calls")
        return False

    # Update the call record
    active_calls[call_id].update_metrics(metrics)

    # No need to save since these are test utilities
    return True
