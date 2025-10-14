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


# NOTE: Metrics update functionality has been removed from this agent service.
# It should be implemented on the call history service that receives call data.
# See documentation below for implementation details.


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


"""
Call Record Retrieval and Analytics Guide

These functions were previously implemented in this module but have been removed
since they're only used for testing purposes. In a production environment, 
these functions should be implemented as part of a dedicated Call History 
Service that receives and stores call data from this agent.

A proper implementation would:

1. Store call records in a persistent database (e.g., PostgreSQL, MongoDB)
2. Provide a REST API to access historical call data
3. Implement proper authentication and authorization
4. Support filtering, pagination, and sorting
5. Include data analytics capabilities

Recommended API endpoints for the Call History Service:

- GET /api/calls/{call_id} - Get details for a specific call
- GET /api/calls/phone/{phone_number} - Get calls for a specific phone number
- GET /api/calls/recent - Get recent calls with pagination
- GET /api/stats - Get call statistics with date filtering
- GET /api/reports/summary - Generate summary reports
- GET /api/reports/csv - Export call data to CSV

For implementation details, refer to the docs/CALL_HISTORY_API.md and
docs/CALL_HISTORY.md documentation files.
"""
