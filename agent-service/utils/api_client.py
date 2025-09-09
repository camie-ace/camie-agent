"""
External API client for making HTTP requests to the Voice Config API
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional, List
import os
import jwt
import time


class APIClient:
    """Client for making external API calls to the Voice Config API"""

    def __init__(self):
        self.session = None
        self.base_headers = {
            "Content-Type": "application/json",
            "User-Agent": "Agent-Service/1.0"
        }

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            headers=self.base_headers,
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        if not self.session:
            raise RuntimeError(
                "APIClient must be used as async context manager")

        try:
            async with self.session.request(method, url, **kwargs) as response:
                response_text = await response.text()

                if response.status >= 400:
                    print(f"API Error {response.status}: {response_text}")
                    return {
                        "error": True,
                        "status_code": response.status,
                        "message": response_text
                    }

                try:
                    return await response.json()
                except json.JSONDecodeError:
                    return {"data": response_text, "raw": True}

        except asyncio.TimeoutError:
            return {"error": True, "message": "Request timeout"}
        except Exception as e:
            return {"error": True, "message": str(e)}

    async def fetch_agent_config(self, phone_number: str, call_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch agent configuration from external API using VOICE_CONFIG_TOKEN_URL

        Args:
            phone_number: Phone number to get config for
            call_type: Optional call direction ("inbound" or "outbound")

        Returns:
            Agent configuration or None
        """
        # Only use VOICE_CONFIG_TOKEN_URL for config fetching
        token_url = os.getenv("VOICE_CONFIG_TOKEN_URL")
        jwt_secret = os.getenv("JWT_SECRET")

        if not token_url or not jwt_secret:
            print(
                "Cannot fetch agent configuration: VOICE_CONFIG_TOKEN_URL or JWT_SECRET not configured")
            return None

        # Create JWT token for authorization
        try:
            now = int(time.time())
            exp = now + 3600

            jwt_payload = {
                "phone_number": phone_number,
                "role": "voice_agent",
                "iat": now,
                "exp": exp,
                "sub": phone_number
            }

            token = jwt.encode(jwt_payload, jwt_secret, algorithm="HS256")

            headers = {"Authorization": f"Bearer {token}"}
            params = {"call_type": call_type} if call_type else None

            print(
                f"Fetching agent config from VOICE_CONFIG_TOKEN_URL for: {phone_number} (call_type={call_type or 'n/a'})")
            result = await self._make_request("GET", token_url, headers=headers, params=params)

            if result.get("responseCode") == "00":
                print(f"Successfully fetched config for {phone_number}")
                return result.get("data")
            elif result.get("responseCode") == "03" and "Agent not found for phone number" in result.get("responseDescription", ""):
                print(
                    f"Agent not found in API for {phone_number}: {result.get('responseDescription')}")
                return None
            elif not result.get("error"):
                # Other responseCode but not an error from the request itself
                print(
                    f"API returned non-success code for {phone_number}: {result.get('responseDescription')}")
                return None
            else:
                print(
                    f"Failed to fetch config for {phone_number}: {result.get('message')}")
                return None
        except Exception as e:
            print(f"Config fetch from VOICE_CONFIG_TOKEN_URL failed: {e}")
            return None


# Global API client instance
api_client = APIClient()
