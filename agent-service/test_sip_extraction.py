#!/usr/bin/env python3
"""
Test script to verify SIP data extraction from Twilio room names
"""

from utils.room_extractor import extract_sip_data_from_room_name
import sys
import os
sys.path.append(
    '/Users/macbookair/Downloads/Docs/Camie/dev/agentApp/agent-service')


def test_twilio_patterns():
    """Test various Twilio room name patterns"""

    test_cases = [
        "twilio-_3693_naxnFCNHxkDu",  # From your logs
        "twilio-trunk-abc123-+1234567890",
        "twilio-trunk123-session456",
        "sip-trunk456-from+1234567890-to+0987654321",
        "regular-room-name"
    ]

    print("Testing SIP data extraction from room names:")
    print("=" * 50)

    for room_name in test_cases:
        print(f"\nRoom name: {room_name}")
        sip_data = extract_sip_data_from_room_name(room_name)
        if sip_data:
            for key, value in sip_data.items():
                print(f"  {key}: {value}")
        else:
            print("  No SIP data extracted")

    print("\n" + "=" * 50)


if __name__ == "__main__":
    test_twilio_patterns()
