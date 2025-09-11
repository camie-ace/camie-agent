#!/usr/bin/env python3
"""
Simple test script to verify room name extraction from job context
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock the LiveKit JobContext for testing


class MockJobRequest:
    def __init__(self, room_name):
        self.room_name = room_name


class MockJob:
    def __init__(self, room_name):
        self.request = MockJobRequest(room_name)

    def __str__(self):
        return f"Job(room_name={self.request.room_name}, id=test)"


class MockJobContext:
    def __init__(self, room_name):
        self.job = MockJob(room_name)

    async def connect(self):
        logger.info("Mock connect called")

# Test function


async def test_room_name_extraction():
    test_room_name = "twilio-+15637482213-ST_Ly7fFQGUr3KD"

    # Create mock context
    ctx = MockJobContext(test_room_name)

    # Extract room name using the same logic as in agent.py
    try:
        room_name = ctx.job.request.room_name
        logger.info(f"Successfully extracted room name: {room_name}")

        # Test fallback extraction
        logger.info(f"Testing fallback extraction:")
        room_name_fallback = str(ctx.job).split("room_name=")[1].split(
            ",")[0] if "room_name=" in str(ctx.job) else "unknown"
        logger.info(f"Fallback room name: {room_name_fallback}")

        assert room_name == test_room_name, "Room name does not match expected value"
        assert room_name_fallback == test_room_name, "Fallback room name does not match expected value"

        return True
    except Exception as e:
        logger.error(f"Error extracting room name: {e}")
        return False

if __name__ == "__main__":
    load_dotenv()
    result = asyncio.run(test_room_name_extraction())
    if result:
        logger.info("✅ Room name extraction test passed!")
        sys.exit(0)
    else:
        logger.error("❌ Room name extraction test failed!")
        sys.exit(1)
