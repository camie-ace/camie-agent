"""
Agent configurations for different business types and use cases
"""

from typing import Dict, Any, Optional
from .config_definitions import DEFAULT_SETTINGS


def get_agent_config(agent_type: str, business_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get agent configuration based on agent type and optional business name

    Args:
        agent_type: Type of agent (technical_support, sales, scheduler, etc.)
        business_name: Optional business name for customization

    Returns:
        Dictionary containing agent configuration
    """

    # Start with default settings as base
    config = DEFAULT_SETTINGS.copy()

    # Customize based on agent type
    if agent_type == "technical_support":
        config.update({
            "assistant_instructions": """You are a technical support assistant. You help users with technical issues, troubleshooting, and product support. Be patient, thorough, and provide step-by-step solutions.""",
            "welcome_message": "Hello! I'm here to help you with any technical issues. How can I assist you today?"
        })

    elif agent_type == "sales":
        config.update({
            "assistant_instructions": """You are a sales assistant. You help customers understand products, answer questions about pricing, and guide them through the purchase process. Be friendly, knowledgeable, and helpful.""",
            "welcome_message": "Hello! I'm here to help you find the perfect solution for your needs. How can I assist you today?"
        })

    elif agent_type == "scheduler":
        config.update({
            "assistant_instructions": """You are a scheduling assistant. You help customers book appointments, manage their calendar, and provide information about availability. Be efficient and organized.""",
            "welcome_message": "Hello! I'm here to help you schedule an appointment. What would you like to book today?"
        })

    elif agent_type == "restaurant":
        config.update({
            "assistant_instructions": """You are a restaurant assistant. You help customers with orders, menu questions, and reservations. Be friendly and knowledgeable about the menu.""",
            "welcome_message": "Welcome! I'm here to help you with your order or any questions about our menu. How can I assist you?"
        })

    elif agent_type == "customer_service":
        config.update({
            "assistant_instructions": """You are a customer service assistant. You help customers with general inquiries, account issues, and provide support. Be professional, empathetic, and solution-oriented.""",
            "welcome_message": "Hello! I'm here to help you with any questions or concerns. How can I assist you today?"
        })

    # For French social housing (default case), keep existing French configuration
    # This is already in DEFAULT_SETTINGS

    return config
