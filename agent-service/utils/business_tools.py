"""
Business tools for dynamic agent configurations
Handles client context, information collection, business logic, and API integrations
"""

from typing import Dict, Any, Callable, List, Optional, Union
import logging
import os
import requests
import json

# Configure logging
logger = logging.getLogger(__name__)

# Specialized tool implementations
# Knowledge Base Tool


async def query_knowledge_base(query: str, context: Dict[str, Any] = None) -> str:
    """
    Query a vector database for knowledge based on the query

    Args:
        query: The search query
        context: Additional context for the query (optional)

    Returns:
        String containing the knowledge base response
    """
    try:
        kb_api_url = os.getenv("KNOWLEDGE_BASE_API_URL")
        if not kb_api_url:
            logger.error("KNOWLEDGE_BASE_API_URL environment variable not set")
            return "I can't access the knowledge base at the moment."

        headers = {"Content-Type": "application/json"}
        payload = {
            "query": query,
            "context": context or {}
        }

        response = requests.post(
            kb_api_url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            return result.get("answer", "I found information but couldn't process it properly.")
        else:
            logger.error(
                f"Knowledge base API returned status {response.status_code}")
            return "I encountered an issue when searching for that information."

    except Exception as e:
        logger.exception(f"Error querying knowledge base: {str(e)}")
        return "I'm having trouble accessing that information right now."

# SMS Sending Tool


async def send_sms(recipient: str, message: str) -> Dict[str, Any]:
    """
    Send an SMS message to the specified recipient

    Args:
        recipient: Phone number to send the SMS to
        message: The message content to send

    Returns:
        Dictionary with success status and message
    """
    try:
        sms_api_url = os.getenv("SMS_API_URL")
        if not sms_api_url:
            logger.error("SMS_API_URL environment variable not set")
            return {"success": False, "message": "SMS service is not configured."}

        headers = {"Content-Type": "application/json"}
        payload = {
            "to": recipient,
            "message": message
        }

        response = requests.post(
            sms_api_url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            return {"success": True, "message": "SMS sent successfully."}
        else:
            error_msg = f"SMS API returned status {response.status_code}"
            logger.error(error_msg)
            return {"success": False, "message": f"Failed to send SMS: {error_msg}"}

    except Exception as e:
        error_msg = f"Error sending SMS: {str(e)}"
        logger.exception(error_msg)
        return {"success": False, "message": error_msg}

# Cal.com Integration Tools


async def calcom_check_availability(date: str, service_type: str = None) -> Dict[str, Any]:
    """
    Check availability on Cal.com for a specific date and service

    Args:
        date: The date to check in ISO format (YYYY-MM-DD)
        service_type: Optional service type to filter available slots

    Returns:
        Dictionary with availability information
    """
    try:
        calcom_api_url = os.getenv("CALCOM_API_URL")
        api_key = os.getenv("CALCOM_API_KEY")

        if not calcom_api_url or not api_key:
            logger.error("Cal.com API configuration missing")
            return {"success": False, "available": False, "message": "Calendar service is not configured."}

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        payload = {
            "date": date,
            "serviceType": service_type
        }

        response = requests.post(
            f"{calcom_api_url}/availability", headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "available": result.get("available", False),
                "slots": result.get("availableSlots", []),
                "message": "Successfully retrieved availability."
            }
        else:
            error_msg = f"Cal.com API returned status {response.status_code}"
            logger.error(error_msg)
            return {"success": False, "available": False, "message": error_msg}

    except Exception as e:
        error_msg = f"Error checking Cal.com availability: {str(e)}"
        logger.exception(error_msg)
        return {"success": False, "available": False, "message": error_msg}


async def calcom_book_appointment(appointment_details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Book an appointment on Cal.com

    Args:
        appointment_details: Dictionary containing appointment details
            (date, time, service_type, name, email, etc.)

    Returns:
        Dictionary with booking status and confirmation details
    """
    try:
        calcom_api_url = os.getenv("CALCOM_API_URL")
        api_key = os.getenv("CALCOM_API_KEY")

        if not calcom_api_url or not api_key:
            logger.error("Cal.com API configuration missing")
            return {"success": False, "message": "Calendar booking service is not configured."}

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        response = requests.post(
            f"{calcom_api_url}/bookings", headers=headers, json=appointment_details, timeout=10)
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "booking_id": result.get("id"),
                "confirmation_link": result.get("confirmationLink", ""),
                "message": "Appointment booked successfully."
            }
        else:
            error_msg = f"Cal.com API returned status {response.status_code}"
            logger.error(error_msg)
            return {"success": False, "message": f"Failed to book appointment: {error_msg}"}

    except Exception as e:
        error_msg = f"Error booking Cal.com appointment: {str(e)}"
        logger.exception(error_msg)
        return {"success": False, "message": error_msg}


async def calcom_modify_booking(booking_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Modify an existing Cal.com booking

    Args:
        booking_id: ID of the booking to modify
        updates: Dictionary containing the fields to update

    Returns:
        Dictionary with modification status
    """
    try:
        calcom_api_url = os.getenv("CALCOM_API_URL")
        api_key = os.getenv("CALCOM_API_KEY")

        if not calcom_api_url or not api_key:
            logger.error("Cal.com API configuration missing")
            return {"success": False, "message": "Calendar service is not configured."}

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        response = requests.patch(
            f"{calcom_api_url}/bookings/{booking_id}",
            headers=headers,
            json=updates,
            timeout=10
        )

        if response.status_code in [200, 204]:
            return {
                "success": True,
                "message": "Booking updated successfully."
            }
        else:
            error_msg = f"Cal.com API returned status {response.status_code}"
            logger.error(error_msg)
            return {"success": False, "message": f"Failed to update booking: {error_msg}"}

    except Exception as e:
        error_msg = f"Error updating Cal.com booking: {str(e)}"
        logger.exception(error_msg)
        return {"success": False, "message": error_msg}

# Google Calendar Integration Tools


async def gcal_check_availability(date: str, service_type: str = None) -> Dict[str, Any]:
    """
    Check availability on Google Calendar for a specific date

    Args:
        date: The date to check in ISO format (YYYY-MM-DD)
        service_type: Optional service type/calendar to check

    Returns:
        Dictionary with availability information
    """
    try:
        gcal_api_url = os.getenv("GCAL_API_URL")
        api_key = os.getenv("GCAL_API_KEY")

        if not gcal_api_url or not api_key:
            logger.error("Google Calendar API configuration missing")
            return {"success": False, "available": False, "message": "Google Calendar service is not configured."}

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        calendar_id = service_type if service_type else "primary"

        response = requests.get(
            f"{gcal_api_url}/calendars/{calendar_id}/free-busy",
            headers=headers,
            params={"date": date},
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "available": not result.get("busy", True),
                "slots": result.get("availableSlots", []),
                "message": "Successfully retrieved availability."
            }
        else:
            error_msg = f"Google Calendar API returned status {response.status_code}"
            logger.error(error_msg)
            return {"success": False, "available": False, "message": error_msg}

    except Exception as e:
        error_msg = f"Error checking Google Calendar availability: {str(e)}"
        logger.exception(error_msg)
        return {"success": False, "available": False, "message": error_msg}


async def gcal_book_appointment(appointment_details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Book an appointment on Google Calendar

    Args:
        appointment_details: Dictionary containing appointment details
            (date, time, summary, description, attendees, etc.)

    Returns:
        Dictionary with booking status and confirmation details
    """
    try:
        gcal_api_url = os.getenv("GCAL_API_URL")
        api_key = os.getenv("GCAL_API_KEY")

        if not gcal_api_url or not api_key:
            logger.error("Google Calendar API configuration missing")
            return {"success": False, "message": "Google Calendar service is not configured."}

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        calendar_id = appointment_details.pop("calendar_id", "primary")

        response = requests.post(
            f"{gcal_api_url}/calendars/{calendar_id}/events",
            headers=headers,
            json=appointment_details,
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "event_id": result.get("id"),
                "link": result.get("htmlLink", ""),
                "message": "Appointment booked successfully on Google Calendar."
            }
        else:
            error_msg = f"Google Calendar API returned status {response.status_code}"
            logger.error(error_msg)
            return {"success": False, "message": f"Failed to book appointment: {error_msg}"}

    except Exception as e:
        error_msg = f"Error booking Google Calendar appointment: {str(e)}"
        logger.exception(error_msg)
        return {"success": False, "message": error_msg}


async def gcal_modify_booking(event_id: str, calendar_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Modify an existing Google Calendar event

    Args:
        event_id: ID of the event to modify
        calendar_id: ID of the calendar containing the event
        updates: Dictionary containing the fields to update

    Returns:
        Dictionary with modification status
    """
    try:
        gcal_api_url = os.getenv("GCAL_API_URL")
        api_key = os.getenv("GCAL_API_KEY")

        if not gcal_api_url or not api_key:
            logger.error("Google Calendar API configuration missing")
            return {"success": False, "message": "Google Calendar service is not configured."}

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        calendar_id = calendar_id or "primary"

        response = requests.patch(
            f"{gcal_api_url}/calendars/{calendar_id}/events/{event_id}",
            headers=headers,
            json=updates,
            timeout=10
        )

        if response.status_code == 200:
            return {
                "success": True,
                "message": "Event updated successfully on Google Calendar."
            }
        else:
            error_msg = f"Google Calendar API returned status {response.status_code}"
            logger.error(error_msg)
            return {"success": False, "message": f"Failed to update event: {error_msg}"}

    except Exception as e:
        error_msg = f"Error updating Google Calendar event: {str(e)}"
        logger.exception(error_msg)
        return {"success": False, "message": error_msg}

# Generic API Action Handler


async def execute_api_action(action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a generic API action

    Args:
        action: The action to perform
        parameters: Parameters for the action

    Returns:
        Dictionary with action result
    """
    try:
        logger.info(
            f"Executing API action: {action} with parameters: {parameters}")

        # Route to appropriate specialized function based on action
        if action == "query_knowledge":
            result = await query_knowledge_base(parameters.get("query", ""), parameters.get("context"))
            return {"success": True, "result": result}
        elif action == "send_sms":
            return await send_sms(parameters.get("recipient"), parameters.get("message"))
        elif action == "check_calcom_availability":
            return await calcom_check_availability(parameters.get("date"), parameters.get("service_type"))
        elif action == "book_calcom_appointment":
            return await calcom_book_appointment(parameters)
        elif action == "modify_calcom_booking":
            return await calcom_modify_booking(parameters.get("booking_id"), parameters.get("updates", {}))
        elif action == "check_gcal_availability":
            return await gcal_check_availability(parameters.get("date"), parameters.get("service_type"))
        elif action == "book_gcal_appointment":
            return await gcal_book_appointment(parameters)
        elif action == "modify_gcal_booking":
            return await gcal_modify_booking(
                parameters.get("event_id"),
                parameters.get("calendar_id"),
                parameters.get("updates", {})
            )
        else:
            logger.warning(f"Unknown API action requested: {action}")
            return {
                "success": False,
                "message": f"The {action} functionality is not recognized."
            }
    except Exception as e:
        error_msg = f"Error executing API action {action}: {str(e)}"
        logger.exception(error_msg)
        return {"success": False, "message": error_msg}


class BusinessSession:
    """
    Session class to manage business interactions
    """

    def __init__(self, business_config: Dict[str, Any] = None):
        self.config = business_config or {}
        self.conversation_context = {
            "stage": "greeting",
            "collected_info": {},
            "last_action": None
        }

    async def get_conversation_context(self) -> Dict[str, Any]:
        """Get the current conversation context"""
        return self.conversation_context

    async def collect_client_info(self, field: str, value: str) -> bool:
        """Collect client information"""
        if field and value:
            self.conversation_context.setdefault(
                "collected_info", {})[field] = value
            return True
        return False

    async def update_conversation_stage(self, stage: str) -> str:
        """Update the conversation stage"""
        self.conversation_context["stage"] = stage
        return stage

    async def query_information(self, query: str) -> str:
        """Query knowledge base with context"""
        return await query_knowledge_base(
            query,
            self.conversation_context
        )

    async def handle_appointment_booking(self, appointment_details: Dict[str, Any]) -> Dict[str, Any]:
        """Handle appointment booking based on config"""
        calendar_type = self.config.get("calendar_type", "calcom")

        if calendar_type == "calcom":
            return await calcom_book_appointment(appointment_details)
        elif calendar_type == "google":
            return await gcal_book_appointment(appointment_details)
        else:
            return {
                "success": False,
                "message": f"Unknown calendar type: {calendar_type}"
            }

    async def check_availability(self, date: str, service_type: str = None) -> Dict[str, Any]:
        """Check availability based on config"""
        calendar_type = self.config.get("calendar_type", "calcom")

        if calendar_type == "calcom":
            return await calcom_check_availability(date, service_type)
        elif calendar_type == "google":
            return await gcal_check_availability(date, service_type)
        else:
            return {
                "success": False,
                "available": False,
                "message": f"Unknown calendar type: {calendar_type}"
            }


class ContextManager:
    """Manages conversation context and state for multiple business types"""

    def __init__(self):
        self.sessions = {}
        self.business_configs = {}

    async def get_session(self, user_id: str, business_config: Dict[str, Any] = None) -> BusinessSession:
        """Get or create a session for a user with specific business configuration"""
        if user_id not in self.sessions:
            self.sessions[user_id] = BusinessSession(business_config)
            if business_config:
                self.business_configs[user_id] = business_config
        return self.sessions[user_id]

    async def clear_session(self, user_id: str):
        """Clear a user's session"""
        if user_id in self.sessions:
            del self.sessions[user_id]
        if user_id in self.business_configs:
            del self.business_configs[user_id]

    async def get_all_sessions(self) -> Dict[str, BusinessSession]:
        """Get all active sessions (for debugging)"""
        return self.sessions

    async def update_business_config(self, user_id: str, business_config: Dict[str, Any]):
        """Update business configuration for an existing session"""
        if user_id in self.sessions:
            # Update existing session with new config
            self.sessions[user_id] = BusinessSession(business_config)
            self.business_configs[user_id] = business_config


# Global context manager instance
context_manager = ContextManager()


async def get_business_context(user_id: str, business_config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Get business context for a user with optional business configuration"""
    session = await context_manager.get_session(user_id, business_config)
    return await session.get_conversation_context()


async def update_client_info(user_id: str, field: str, value: str) -> bool:
    """Update client information for a user"""
    session = await context_manager.get_session(user_id)
    return await session.collect_client_info(field, value)


async def advance_conversation_stage(user_id: str, stage: str) -> str:
    """Advance conversation to next stage"""
    session = await context_manager.get_session(user_id)
    return await session.update_conversation_stage(stage)


async def query_user_information(user_id: str, query: str) -> str:
    """Query knowledge base for user-specific information"""
    session = await context_manager.get_session(user_id)
    return await session.query_information(query)


async def book_user_appointment(user_id: str, appointment_details: Dict[str, Any]) -> Dict[str, Any]:
    """Book appointment for user"""
    session = await context_manager.get_session(user_id)
    return await session.handle_appointment_booking(appointment_details)


async def check_user_availability(user_id: str, date: str, service_type: str = None) -> Dict[str, Any]:
    """Check availability for user"""
    session = await context_manager.get_session(user_id)
    return await session.check_availability(date, service_type)


def get_tool_by_name(tool_name: str) -> Optional[Callable]:
    """
    Get a callable tool function by name

    Args:
        tool_name: The name of the tool to get

    Returns:
        Callable function for the requested tool, or None if not found
    """
    tools_map = {
        "knowledge_base": query_knowledge_base,
        "sms": send_sms,

        # Cal.com tools
        "calcom_availability": calcom_check_availability,
        "calcom_booking": calcom_book_appointment,
        "calcom_modify": calcom_modify_booking,

        # Google Calendar tools
        "gcal_availability": gcal_check_availability,
        "gcal_booking": gcal_book_appointment,
        "gcal_modify": gcal_modify_booking,

        # Business context tools
        "get_business_context": get_business_context,
        "update_client_info": update_client_info,
        "advance_conversation": advance_conversation_stage,
        "query_user_info": query_user_information,
        "book_appointment": book_user_appointment,
        "check_availability": check_user_availability
    }

    return tools_map.get(tool_name)
