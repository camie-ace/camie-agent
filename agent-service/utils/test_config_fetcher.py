"""
Unit tests for config_fetcher utilities
"""
import asyncio
import os
import jwt
import unittest
from unittest.mock import patch, MagicMock

from utils.config_fetcher import (
    extract_phone_from_room_name,
    create_phone_jwt,
    fetch_agent_config_by_phone,
    get_agent_config_from_room
)


class TestConfigFetcher(unittest.TestCase):
    """Test cases for config_fetcher module"""

    def test_extract_phone_from_room_name(self):
        """Test phone number extraction from room name"""
        # Set up test cases
        test_cases = [
            # Valid format with different phone numbers
            ("twilio-+15637482213-ST_Ly7fFQGUr3KD", "+15637482213"),
            ("twilio-+33644644937-ST_ABCDEFG", "+33644644937"),
            # Invalid formats
            ("invalid-room-name", None),
            ("twilio-invalid-ST_123456", None),
            ("", None),
        ]

        for room_name, expected in test_cases:
            result = asyncio.run(extract_phone_from_room_name(room_name))
            self.assertEqual(result, expected,
                             f"Failed for room name: {room_name}")

    @patch.dict(os.environ, {"JWT_SECRET": "test_secret", "JWT_ALGORITHM": "HS256"})
    def test_create_phone_jwt(self):
        """Test JWT token creation for phone numbers"""
        phone_number = "+15637482213"
        token = asyncio.run(create_phone_jwt(phone_number))

        # Verify token can be decoded and contains correct payload
        decoded = jwt.decode(token, "test_secret", algorithms=["HS256"])
        self.assertEqual(decoded, {"phone_number": phone_number})

    @patch.dict(os.environ, {
        "JWT_SECRET": "test_secret",
        "JWT_ALGORITHM": "HS256",
        "VOICE_CONFIG_TOKEN_URL": "https://settings.camie.tech/api/v1/voice-config/get-by-token/"
    })
    @patch("utils.config_fetcher.APIClient")
    def test_fetch_agent_config_by_phone(self, mock_api_client):
        """Test fetching agent config by phone number"""
        # Mock the API client
        mock_client_instance = MagicMock()
        mock_api_client.return_value.__aenter__.return_value = mock_client_instance

        # Mock the response from _make_request
        mock_response = {
            "phone_number": {
                "inbound": {"stt": {"model": "nova-3"}, "llm": {"model": "gpt-4o"}},
                "outbound": {"stt": {"model": "nova-2"}, "llm": {"model": "gpt-3.5"}}
            }
        }

        # Create a mock awaitable that returns the response
        async def mock_make_request(*args, **kwargs):
            return mock_response

        mock_client_instance._make_request = mock_make_request

        # Test with no call direction (should default to inbound)
        config, direction = asyncio.run(
            fetch_agent_config_by_phone("+15637482213"))
        self.assertEqual(direction, "inbound")
        self.assertEqual(config, mock_response["phone_number"]["inbound"])

        # Test with specific call direction
        config, direction = asyncio.run(
            fetch_agent_config_by_phone("+15637482213", "outbound"))
        self.assertEqual(direction, "outbound")
        self.assertEqual(config, mock_response["phone_number"]["outbound"])

    @patch("utils.config_fetcher.extract_phone_from_room_name")
    @patch("utils.config_fetcher.fetch_agent_config_by_phone")
    def test_get_agent_config_from_room(self, mock_fetch_config, mock_extract_phone):
        """Test getting agent config from room name and metadata"""
        # Setup mocks
        mock_extract_phone.return_value = "+15637482213"
        mock_fetch_config.return_value = (
            {"stt": {"model": "test-model"}}, "inbound")

        # Test with metadata containing direction
        metadata = {"direction": "inbound"}
        config = asyncio.run(get_agent_config_from_room("test-room", metadata))

        # Verify the correct calls were made
        mock_extract_phone.assert_called_with("test-room")
        mock_fetch_config.assert_called_with("+15637482213", "inbound")
        self.assertEqual(config, {"stt": {"model": "test-model"}})


if __name__ == "__main__":
    unittest.main()
