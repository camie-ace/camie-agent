#!/usr/bin/env python3
"""
Call History Test Script

This script tests the call history functionality by simulating call events
and verifying that they are correctly recorded. It doesn't require an actual
LiveKit connection.

Usage:
    python test_call_history.py
"""

from utils.call_history import (
    start_call_recording,
    update_call_config,
    update_call_stage,
    end_call_recording
)
from utils.call_history_test_utils import (
    update_call_metrics,
    get_call_record,
    get_recent_calls
)
import os
import sys
import asyncio
import json
import datetime
import uuid
import random
from typing import Dict, List, Any, Optional

# Add parent directory to path to allow importing modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)


async def simulate_call(phone_number: str) -> str:
    """
    Simulate a complete call and track it in call history

    Args:
        phone_number: Phone number for the call

    Returns:
        call_id: The ID of the simulated call
    """
    print(f"Simulating call for phone number: {phone_number}")

    # Generate a random room name (similar to actual LiveKit format)
    random_id = str(uuid.uuid4()).replace('-', '')[:12]
    room_name = f"livekit-{phone_number}-{random_id}"

    # Start call recording
    call_id = await start_call_recording(
        phone_number=phone_number,
        room_name=room_name,
        call_type="inbound"
    )
    print(f"Started call recording with ID: {call_id}")

    # Simulate agent configuration
    agent_config = {
        "stt_config_key": "DEEPGRAM_NOVA2_EN",
        "llm_config_key": "OPENAI_GPT4O_MINI",
        "tts_config_key": "ELEVENLABS_DEFAULT_EN",
        "business_config": {
            "business_type": "test_business",
            "language": "english"
        }
    }

    # Update call config
    await update_call_config(call_id, agent_config)
    print("Updated call configuration")

    # Simulate conversation stages
    stages = ["greeting", "discovery", "solution", "closing"]
    for stage in stages:
        # Add a delay to simulate conversation time
        await asyncio.sleep(0.5)

        # Update the stage
        await update_call_stage(call_id, stage)
        print(f"Updated call stage to: {stage}")

    # Simulate call metrics
    metrics = {
        "total_user_utterances": random.randint(5, 15),
        "total_agent_utterances": random.randint(5, 15),
        "longest_user_utterance": random.randint(10, 50),
        "longest_agent_utterance": random.randint(10, 60),
        "average_user_response_time": random.uniform(1.0, 5.0),
        "average_agent_response_time": random.uniform(0.5, 2.0),
        "silence_count": random.randint(0, 5),
        "interruption_count": random.randint(0, 3)
    }

    # Update call metrics
    await update_call_metrics(call_id, metrics)
    print("Updated call metrics")

    # Simulate call outcomes
    outcomes = {
        "completion_rate": random.uniform(0.7, 1.0),
        "fields_collected": ["name", "industry", "company_size"],
        "final_stage": "closing",
        "successful": True,
        "notes": "Test call completed successfully"
    }

    # End the call
    await end_call_recording(
        call_id=call_id,
        status="completed",
        outcomes=outcomes
    )
    print("Ended call recording with status: completed")

    return call_id


async def verify_call_record(call_id: str) -> bool:
    """
    Verify that a call record exists and has the expected fields

    Args:
        call_id: ID of the call to verify

    Returns:
        bool: True if verification passed, False otherwise
    """
    print(f"\nVerifying call record: {call_id}")

    # Get the call record
    call_record = await get_call_record(call_id)

    if not call_record:
        print(f"ERROR: Call record not found for ID: {call_id}")
        return False

    # Verify required fields
    required_fields = [
        "call_id", "phone_number", "room_name", "start_time", "end_time",
        "duration_seconds", "status", "agent_config", "metrics", "outcomes"
    ]

    missing_fields = []
    for field in required_fields:
        if field not in call_record:
            missing_fields.append(field)

    if missing_fields:
        print(f"ERROR: Missing required fields: {', '.join(missing_fields)}")
        return False

    # Verify that duration was calculated
    if call_record.get("duration_seconds") is None or call_record.get("duration_seconds") <= 0:
        print("ERROR: Call duration was not properly calculated")
        return False

    # Verify nested fields
    if not call_record.get("agent_config", {}).get("business_type"):
        print("ERROR: Missing agent_config.business_type")
        return False

    if not call_record.get("metrics", {}).get("total_user_utterances"):
        print("ERROR: Missing metrics.total_user_utterances")
        return False

    if not call_record.get("outcomes", {}).get("completion_rate"):
        print("ERROR: Missing outcomes.completion_rate")
        return False

    print("Verification PASSED: Call record contains all required fields")
    print(
        f"Call duration: {call_record.get('duration_seconds', 0):.2f} seconds")
    print(
        f"Business type: {call_record.get('agent_config', {}).get('business_type', 'unknown')}")
    print(
        f"Completion rate: {call_record.get('outcomes', {}).get('completion_rate', 0):.2%}")

    return True


async def main():
    # Generate some test phone numbers
    test_phones = [
        "+15551234567",
        "+15559876543",
        "+15552223333",
    ]

    # Clear call_records.json if it exists (for clean test)
    call_history_file = os.path.join(
        parent_dir, "data", "call_history", "call_records.json")
    if os.path.exists(call_history_file):
        print(f"Backing up existing call records to {call_history_file}.bak")
        os.rename(call_history_file, f"{call_history_file}.bak")

    # Simulate multiple calls
    call_ids = []
    for phone in test_phones:
        call_id = await simulate_call(phone)
        call_ids.append(call_id)
        # Add a small delay between calls
        await asyncio.sleep(1)

    # Verify each call record
    for call_id in call_ids:
        success = await verify_call_record(call_id)
        if not success:
            print(f"Test failed for call ID: {call_id}")

    # Get recent calls
    recent_calls = await get_recent_calls(10)
    print(f"\nFound {len(recent_calls)} recent calls")

    # Print call summary
    print("\nCall History Summary:")
    for i, call in enumerate(recent_calls, 1):
        print(f"{i}. Call ID: {call.get('call_id')}")
        print(f"   Phone: {call.get('phone_number')}")
        print(f"   Duration: {call.get('duration_seconds', 0):.2f}s")
        print(f"   Status: {call.get('status')}")
        print(
            f"   Business: {call.get('agent_config', {}).get('business_type', 'unknown')}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
