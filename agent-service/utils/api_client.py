"""
External API client for making HTTP requests to various endpoints
Handles vector database queries, appointment booking, and other external integrations
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import os
import jwt
import time


class APIClient:
    """Client for making external API calls"""

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

    async def query_vector_database(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Query vector database for relevant information

        Args:
            query: Natural language query from the caller
            context: Additional context (user info, business type, etc.)

        Returns:
            Dictionary with query results and metadata
        """
        # Vector DB endpoint (replace with your actual endpoint)
        vector_db_url = os.getenv(
            "VECTOR_DB_URL", "https://api.example.com/vector/query")

        payload = {
            "query": query,
            "context": context or {},
            "max_results": 5,
            "threshold": 0.7,
            "business_type": context.get("business_type", "default") if context else "default"
        }

        print(f"Querying vector database: {query}")
        result = await self._make_request("POST", vector_db_url, json=payload)

        if result.get("error"):
            return {
                "success": False,
                "message": "Unable to retrieve information at this time",
                "query": query
            }

        return {
            "success": True,
            "query": query,
            "results": result.get("results", []),
            "confidence": result.get("confidence", 0.0),
            "sources": result.get("sources", [])
        }

    async def fetch_agent_config(self, phone_number: str, call_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch agent configuration from external API/database

        Args:
            phone_number: Phone number to get config for
            call_type: Optional call direction ("inbound" or "outbound")

        Returns:
            Agent configuration or None
        """
        # Get token-based endpoint details
        token_url = (
            os.getenv("VOICE_CONFIG_TOKEN_URL")
            or (os.getenv("BACKEND_BASE_URL") + "/api/v1/voice-config/get-by-token/")
            if os.getenv("BACKEND_BASE_URL")
            else None
        )
        jwt_secret = os.getenv("JWT_SECRET")

        if not token_url or not jwt_secret:
            print(
                "Cannot fetch agent configuration: Token URL or JWT secret not configured")
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
                f"Fetching agent config by token for: {phone_number} (call_type={call_type or 'n/a'})")
            result = await self._make_request("GET", token_url, headers=headers, params=params)

            if result.get("responseCode") == "00":
                print(f"Successfully fetched config for {phone_number}")
                return result.get("data")
            elif result.get("responseCode") == "03" and "Agent not found for phone number" in result.get("responseDescription", ""):
                print(
                    f"Agent not found in database for {phone_number}: {result.get('responseDescription')}")
                return None
            elif not result.get("error"):
                # Other responseCode but not an error from the request itself
                print(
                    f"API returned non-success code for {phone_number}: {result.get('responseDescription')}")
                return None
            else:
                print(
                    f"Failed to fetch token-based config for {phone_number}: {result.get('message')}")
                return None
        except Exception as e:
            print(f"Token-based config fetch failed: {e}")
            return None

    async def book_appointment(self, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Book an appointment through external API

        Args:
            appointment_data: Appointment details (name, date, time, service, etc.)

        Returns:
            Booking result with confirmation details
        """
        booking_api_url = os.getenv(
            "BOOKING_API_URL", "https://api.example.com/appointments/book")

        payload = {
            "customer_name": appointment_data.get("customer_name"),
            "phone_number": appointment_data.get("phone_number"),
            "email": appointment_data.get("email"),
            "service_type": appointment_data.get("service_type"),
            "preferred_date": appointment_data.get("preferred_date"),
            "preferred_time": appointment_data.get("preferred_time"),
            "notes": appointment_data.get("notes", ""),
            "business_type": appointment_data.get("business_type", "default"),
            "created_at": datetime.now().isoformat()
        }

        print(
            f"Booking appointment for: {appointment_data.get('customer_name')}")
        result = await self._make_request("POST", booking_api_url, json=payload)

        if result.get("error"):
            return {
                "success": False,
                "message": "Unable to book appointment at this time. Please try again later.",
                "error_details": result.get("message")
            }

        return {
            "success": True,
            "confirmation_id": result.get("confirmation_id"),
            "appointment_date": result.get("scheduled_date"),
            "appointment_time": result.get("scheduled_time"),
            "message": "Appointment successfully booked!"
        }

    async def check_availability(self, date: str, service_type: str = None) -> Dict[str, Any]:
        """
        Check appointment availability for a specific date

        Args:
            date: Date to check (YYYY-MM-DD format)
            service_type: Optional service type filter

        Returns:
            Available time slots
        """
        availability_api_url = os.getenv(
            "AVAILABILITY_API_URL", "https://api.example.com/appointments/availability")

        params = {
            "date": date,
            "service_type": service_type or "general"
        }

        print(f"Checking availability for: {date}")
        result = await self._make_request("GET", availability_api_url, params=params)

        if result.get("error"):
            return {
                "success": False,
                "message": "Unable to check availability",
                "available_slots": []
            }

        return {
            "success": True,
            "date": date,
            "available_slots": result.get("available_slots", []),
            "fully_booked": len(result.get("available_slots", [])) == 0
        }

    async def update_crm_contact(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update or create contact in CRM system

        Args:
            contact_data: Contact information and interaction details

        Returns:
            CRM update result
        """
        crm_api_url = os.getenv(
            "CRM_API_URL", "https://api.example.com/crm/contacts")

        payload = {
            "phone_number": contact_data.get("phone_number"),
            "name": contact_data.get("name"),
            "email": contact_data.get("email"),
            "company": contact_data.get("company"),
            "interaction_type": contact_data.get("interaction_type", "phone_call"),
            "notes": contact_data.get("notes", ""),
            "lead_score": contact_data.get("lead_score", 0),
            "stage": contact_data.get("stage", "new"),
            "updated_at": datetime.now().isoformat()
        }

        print(f"Updating CRM for: {contact_data.get('name')}")
        result = await self._make_request("POST", crm_api_url, json=payload)

        return {
            "success": not result.get("error", False),
            "contact_id": result.get("contact_id"),
            "message": result.get("message", "Contact updated successfully")
        }

    async def send_follow_up(self, follow_up_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send follow-up communication (email, SMS, etc.)

        Args:
            follow_up_data: Follow-up details and recipient info

        Returns:
            Send result
        """
        follow_up_api_url = os.getenv(
            "FOLLOW_UP_API_URL", "https://api.example.com/communications/send")

        payload = {
            "recipient_phone": follow_up_data.get("phone_number"),
            "recipient_email": follow_up_data.get("email"),
            "message_type": follow_up_data.get("message_type", "email"),
            "template": follow_up_data.get("template", "default"),
            "personalization": follow_up_data.get("personalization", {}),
            "schedule_time": follow_up_data.get("schedule_time"),
            "business_type": follow_up_data.get("business_type", "default")
        }

        print(f"Sending follow-up to: {follow_up_data.get('phone_number')}")
        result = await self._make_request("POST", follow_up_api_url, json=payload)

        return {
            "success": not result.get("error", False),
            "message_id": result.get("message_id"),
            "scheduled_for": result.get("scheduled_for"),
            "message": "Follow-up scheduled successfully" if not result.get("error") else "Failed to schedule follow-up"
        }


# Global API client instance
api_client = APIClient()


async def query_knowledge_base(query: str, context: Dict[str, Any] = None) -> str:
    """
    Query vector database and return formatted response for the agent

    Args:
        query: User's question or request
        context: Additional context about the conversation

    Returns:
        Formatted response string for the agent to use
    """
    async with APIClient() as client:
        result = await client.query_vector_database(query, context)

        if not result.get("success"):
            return "I don't have specific information about that right now. Let me see how else I can help you."

        results = result.get("results", [])
        if not results:
            return "I don't have specific information about that topic. Is there something else I can help you with?"

        # Format the response based on results
        response_parts = []
        for item in results[:2]:  # Use top 2 results
            content = item.get("content", "")
            if content:
                response_parts.append(content)

        if response_parts:
            formatted_response = " ".join(response_parts)
            # Limit response length for conversational flow
            if len(formatted_response) > 200:
                formatted_response = formatted_response[:200] + "..."
            return formatted_response

        return "I found some information but it's not clear enough to share. Could you rephrase your question?"


async def execute_api_action(action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute various API actions based on agent needs

    Args:
        action: Action type (book_appointment, check_availability, etc.)
        parameters: Action parameters

    Returns:
        Action result
    """
    async with APIClient() as client:
        if action == "book_appointment":
            return await client.book_appointment(parameters)
        elif action == "check_availability":
            return await client.check_availability(
                parameters.get("date"),
                parameters.get("service_type")
            )
        elif action == "update_crm":
            return await client.update_crm_contact(parameters)
        elif action == "send_follow_up":
            return await client.send_follow_up(parameters)
        else:
            return {
                "success": False,
                "message": f"Unknown action: {action}"
            }
