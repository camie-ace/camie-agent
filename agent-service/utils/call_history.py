"""
Call History Module

This module manages the recording of call history data for the agent service.
It provides functions to:
1. Create new call records when calls start
2. Update records when calls end
3. Send call data to an external API endpoint

Instead of storing data locally, all call history is sent to the configured
CALL_HISTORY_ENDPOINT when a call ends.
"""

import os
import json
import time
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

# Import API client
from utils.api_client import send_call_history

# Configure logging
logger = logging.getLogger(__name__)

# In-memory cache of active calls (call_id -> CallRecord)


class CallRecord:
    """Represents a single call record with all relevant metadata"""

    def __init__(self,
                 phone_number: str,
                 room_name: str,
                 call_type: str = "inbound",
                 call_id: Optional[str] = None):
        """
        Initialize a new call record

        Args:
            phone_number: The phone number associated with the call
            room_name: The LiveKit room name for the call
            call_type: Call direction ("inbound" or "outbound")
            call_id: Optional ID for the call (will generate UUID if None)
        """
        # Basic call identification
        self.call_id = call_id or str(uuid.uuid4())
        self.phone_number = phone_number
        self.room_name = room_name
        self.call_type = call_type

        # Timestamps
        self.start_time = datetime.now().isoformat()
        self.end_time = None
        self.duration_seconds = None

        # Call status
        self.status = "started"  # started, completed, failed, dropped
        self.termination_reason = None

        # Agent configuration used
        self.agent_config = {
            "stt_config_key": None,
            "llm_config_key": None,
            "tts_config_key": None,
            "business_type": None,
            "language": None
        }

        # Call metrics
        self.metrics = {
            "total_user_utterances": 0,
            "total_agent_utterances": 0,
            "longest_user_utterance": 0,
            "longest_agent_utterance": 0,
            "average_user_response_time": 0,
            "average_agent_response_time": 0,
            "silence_count": 0,
            "interruption_count": 0
        }

        # Call outcomes (to be determined by analyzing the conversation)
        self.outcomes = {
            "completion_rate": 0,
            "fields_collected": [],
            "final_stage": None,
            "successful": None,  # Boolean to indicate call success
            "notes": None        # Any additional notes about the call outcome
        }

        # Conversation stage timeline
        self.stage_timeline = []
    """Represents a single call record with all relevant metadata"""

    def __init__(self,
                 phone_number: str,
                 room_name: str,
                 call_type: str = "inbound",
                 call_id: Optional[str] = None):
        """
        Initialize a new call record

        Args:
            phone_number: The phone number associated with the call
            room_name: The LiveKit room name for the call
            call_type: Call direction ("inbound" or "outbound")
            call_id: Optional ID for the call (will generate UUID if None)
        """
        # Basic call identification
        self.call_id = call_id or str(uuid.uuid4())
        self.phone_number = phone_number
        self.room_name = room_name
        self.call_type = call_type

        # Timestamps
        self.start_time = datetime.now().isoformat()
        self.end_time = None
        self.duration_seconds = None

        # Call status
        self.status = "started"  # started, completed, failed, dropped
        self.termination_reason = None

        # Agent configuration used
        self.agent_config = {
            "stt_config_key": None,
            "llm_config_key": None,
            "tts_config_key": None,
            "business_type": None,
            "language": None
        }

        # Call metrics
        self.metrics = {
            "total_user_utterances": 0,
            "total_agent_utterances": 0,
            "longest_user_utterance": 0,
            "longest_agent_utterance": 0,
            "average_user_response_time": 0,
            "average_agent_response_time": 0,
            "silence_count": 0,
            "interruption_count": 0
        }

        # Call outcomes (to be determined by analyzing the conversation)
        self.outcomes = {
            "completion_rate": 0,
            "fields_collected": [],
            "final_stage": None,
            "successful": None,  # Boolean to indicate call success
            "notes": None        # Any additional notes about the call outcome
        }

        # Conversation stage timeline
        self.stage_timeline = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert the call record to a dictionary for storage"""
        return self.__dict__

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CallRecord':
        """Create a CallRecord instance from a dictionary"""
        record = cls(
            phone_number=data.get('phone_number', 'unknown'),
            room_name=data.get('room_name', 'unknown'),
            call_type=data.get('call_type', 'inbound'),
            call_id=data.get('call_id')
        )

        # Restore all other fields from the data
        for key, value in data.items():
            if key not in ['phone_number', 'room_name', 'call_type', 'call_id']:
                setattr(record, key, value)

        return record

    def update_config(self, agent_config: Dict[str, Any]) -> None:
        """Update the agent configuration used for this call"""
        if not agent_config:
            return

        # Extract relevant configuration details
        self.agent_config = {
            "stt_config_key": agent_config.get("stt_config_key", "unknown"),
            "llm_config_key": agent_config.get("llm_config_key", "unknown"),
            "tts_config_key": agent_config.get("tts_config_key", "unknown"),
            "business_type": agent_config.get("business_config", {}).get("business_type", "unknown"),
            "language": agent_config.get("business_config", {}).get("language", "english")
        }

    def update_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update call metrics during the call"""
        if not metrics:
            return

        # Update metrics with new values
        self.metrics.update(metrics)

    def update_stage(self, stage: str) -> None:
        """Record a stage transition in the conversation"""
        self.stage_timeline.append({
            "stage": stage,
            "timestamp": datetime.now().isoformat()
        })

        # Update the final stage in the outcomes
        self.outcomes["final_stage"] = stage

    def complete_call(self, status: str = "completed", reason: Optional[str] = None,
                      outcomes: Optional[Dict[str, Any]] = None) -> None:
        """
        Mark the call as complete and record final metrics

        Args:
            status: Final call status (completed, failed, dropped)
            reason: Reason for call termination
            outcomes: Final outcomes from the call
        """
        self.end_time = datetime.now().isoformat()
        self.status = status
        self.termination_reason = reason

        # Calculate duration
        if self.start_time:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time)
            self.duration_seconds = (end - start).total_seconds()

        # Update outcomes if provided
        if outcomes:
            self.outcomes.update(outcomes)


# In-memory cache of active calls (call_id -> CallRecord)
active_calls: Dict[str, CallRecord] = {}


async def _save_call_record(call_record: Dict[str, Any]) -> bool:
    """
    Save a call record to memory (will be sent to API when call ends)
    """
    # In this implementation, we just keep the record in memory
    # It will be sent to the API endpoint when the call ends
    return True


async def start_call_recording(phone_number: str, room_name: str,
                               call_type: str = "inbound") -> str:
    """
    Start recording a new call

    Args:
        phone_number: The phone number associated with the call
        room_name: The LiveKit room name for the call
        call_type: Call direction ("inbound" or "outbound")

    Returns:
        call_id: The ID of the new call record
    """
    # Create a new call record
    call_record = CallRecord(
        phone_number=phone_number,
        room_name=room_name,
        call_type=call_type
    )

    # Store in active calls
    call_id = call_record.call_id
    active_calls[call_id] = call_record

    # Save to storage
    await _save_call_record(call_record.to_dict())

    logger.info(f"Started recording call {call_id} for {phone_number}")
    return call_id


async def update_call_config(call_id: str, agent_config: Dict[str, Any]) -> bool:
    """
    Update the configuration used for a call

    Args:
        call_id: The ID of the call to update
        agent_config: The agent configuration used for the call

    Returns:
        bool: True if successful, False otherwise
    """
    # Check if call is in active calls
    if call_id not in active_calls:
        logger.warning(f"Call {call_id} not found in active calls")
        return False

    # Update the call record
    active_calls[call_id].update_config(agent_config)

    # Save to storage
    return await _save_call_record(active_calls[call_id].to_dict())


async def update_call_stage(call_id: str, stage: str) -> bool:
    """
    Update the current stage of a call

    Args:
        call_id: The ID of the call to update
        stage: The new stage of the conversation

    Returns:
        bool: True if successful, False otherwise
    """
    # Check if call is in active calls
    if call_id not in active_calls:
        logger.warning(f"Call {call_id} not found in active calls")
        return False

    # Update the call record
    active_calls[call_id].update_stage(stage)

    # Save to storage
    return await _save_call_record(active_calls[call_id].to_dict())


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

    # Save to storage
    return await _save_call_record(active_calls[call_id].to_dict())


async def end_call_recording(call_id: str, status: str = "completed",
                             reason: Optional[str] = None,
                             outcomes: Optional[Dict[str, Any]] = None) -> bool:
    """
    End recording a call and send data to API endpoint

    Args:
        call_id: The ID of the call to end
        status: Final call status (completed, failed, dropped)
        reason: Reason for call termination
        outcomes: Final outcomes from the call

    Returns:
        bool: True if successful, False otherwise
    """
    # Check if call is in active calls
    if call_id not in active_calls:
        logger.warning(f"Call {call_id} not found in active calls")
        return False

    # Update the call record
    active_calls[call_id].complete_call(status, reason, outcomes)

    # Get the updated record
    call_record = active_calls[call_id]

    # Remove from active calls
    call_record_dict = active_calls.pop(call_id).to_dict()

    # Send to API endpoint
    response = await send_call_history(call_record_dict)

    if response.get("error"):
        logger.error(
            f"Failed to send call history data: {response.get('message')}")
        success = False
    else:
        logger.info(f"Successfully sent call history data to API endpoint")
        success = True

    if success:
        logger.info(
            f"Ended call {call_id} with status {status}, duration: {call_record.duration_seconds}s")

    return success


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
