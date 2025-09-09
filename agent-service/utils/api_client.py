"""
External API client for making HTTP requests to the voice config endpoint
Handles fetching agent configuration from the token-based endpoint
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional
import os
import jwt
import re


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
        print("DEBUG: Creating new aiohttp.ClientSession with base headers:",
              self.base_headers)
        self.session = aiohttp.ClientSession(
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

        # Ensure HTTPS protocol is used
        url = ensure_https_url(url)

        try:
            async with self.session.request(method, url, **kwargs) as response:
                response_text = await response.text()
                print(f"DEBUG: Response status code: {response.status}")
                print(f"DEBUG: Response headers: {dict(response.headers)}")

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
        Fetch agent configuration from external API using token-based endpoint

        Args:
            phone_number: Phone number to get config for
            call_type: Optional call direction ("inbound" or "outbound")

        Returns:
            Agent configuration or None
        """
        # Token-based endpoint with JWT Authorization
        token_url = os.getenv("VOICE_CONFIG_TOKEN_URL")
        jwt_secret = os.getenv("JWT_SECRET")

        # Ensure the URL uses HTTPS protocol
        if token_url:
            token_url = ensure_https_url(token_url)

        if token_url and jwt_secret:
            try:
                jwt_payload = {"phone_number": phone_number}
                token = jwt.encode(jwt_payload, jwt_secret, algorithm="HS256")
                headers = {"Authorization": f"Bearer {token}"}
                params = {"call_type": call_type} if call_type else None

                print(
                    f"Fetching agent config by token for: {phone_number} (call_type={call_type or 'n/a'})")
                result = await self._make_request(
                    "GET", token_url, headers=headers, params=params)

                if not result.get("error"):
                    # Some APIs wrap results in { config: {...} } or { data: {...} }
                    return result.get("config") or result.get("data") or result
                else:
                    print(
                        f"Failed to fetch token-based config for {phone_number}: {result.get('message')}")
            except Exception as e:
                print(f"Token-based config fetch failed: {e}")

        return None


# Global API client instance
api_client = APIClient()


def ensure_https_url(url: str) -> str:
    """
    Ensures a URL uses HTTPS protocol instead of HTTP

    Args:
        url: The URL to check and potentially modify

    Returns:
        URL with HTTPS protocol
    """
    if url and url.startswith("http://"):
        return url.replace("http://", "https://", 1)
    return url


async def query_knowledge_base(query: str, context: Dict[str, Any] = None) -> str:
    """
    Mock function to replace external vector database query

    Args:
        query: User's question or request
        context: Additional context about the conversation

    Returns:
        Mock response for the agent to use
    """
    return "I don't have specific information about that right now. Let me see how else I can help you."


async def execute_api_action(action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mock function to replace external API actions

    Args:
        action: Action type (book_appointment, check_availability, etc.)
        parameters: Action parameters

    Returns:
        Mock action result
    """
    return {
        "success": False,
        "message": f"External API actions are not available: {action}"
    }
