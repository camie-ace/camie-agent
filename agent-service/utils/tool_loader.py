"""
Tool loader for agent business tools.

This module manages the loading and configuration of business tools
such as knowledge base, SMS, calendar integrations, etc.
"""

import os
import logging
from typing import List, Callable, Dict
from utils.config_processor import ToolConfig
from utils.business_tools import get_tool_by_name

logger = logging.getLogger(__name__)


class ToolLoader:
    """Loads and configures business tools based on agent configuration"""

    @staticmethod
    async def load_tools(tool_configs: Dict[str, ToolConfig]) -> List[Callable]:
        """
        Load tools based on agent configuration

        Args:
            tool_configs: Dictionary mapping tool names to their configurations

        Returns:
            List of callable tool functions
        """
        tools_list = []

        if not tool_configs:
            return tools_list

        # Knowledge base tool
        if tool_configs.get("knowledge_base") and tool_configs["knowledge_base"].enabled:
            knowledge_tool = get_tool_by_name("knowledge_base")
            if knowledge_tool:
                # Pass the configuration to the tool via environment variables if needed
                if tool_configs["knowledge_base"].url:
                    os.environ["KNOWLEDGE_BASE_API_URL"] = tool_configs["knowledge_base"].url
                tools_list.append(knowledge_tool)
                logger.info("Loaded knowledge base tool")

        # SMS tool
        if tool_configs.get("sms") and tool_configs["sms"].enabled:
            sms_tool = get_tool_by_name("sms")
            if sms_tool:
                if tool_configs["sms"].url:
                    os.environ["SMS_API_URL"] = tool_configs["sms"].url
                tools_list.append(sms_tool)
                logger.info("Loaded SMS tool")

        # Calendar tools
        if tool_configs.get("calendar") and tool_configs["calendar"].enabled:
            calendar_config = tool_configs["calendar"]
            calendar_metadata = calendar_config.metadata or {}
            calendar_system = calendar_metadata.get("system", "calcom")

            # Set calendar API URL if provided
            if calendar_config.url:
                if calendar_system == "calcom":
                    os.environ["CALCOM_API_URL"] = calendar_config.url
                elif calendar_system == "google":
                    os.environ["GCAL_API_URL"] = calendar_config.url

            # Set additional metadata like API keys if provided
            if calendar_metadata.get("api_key"):
                if calendar_system == "calcom":
                    os.environ["CALCOM_API_KEY"] = calendar_metadata["api_key"]
                elif calendar_system == "google":
                    os.environ["GCAL_API_KEY"] = calendar_metadata["api_key"]

            # Load appropriate calendar tools based on system
            if calendar_system == "calcom":
                # Add Cal.com tools
                for tool_name in ["calcom_availability", "calcom_booking", "calcom_modify"]:
                    tool = get_tool_by_name(tool_name)
                    if tool:
                        tools_list.append(tool)
                logger.info("Loaded Cal.com calendar tools")
            elif calendar_system == "google":
                # Add Google Calendar tools
                for tool_name in ["gcal_availability", "gcal_booking", "gcal_modify"]:
                    tool = get_tool_by_name(tool_name)
                    if tool:
                        tools_list.append(tool)
                logger.info("Loaded Google Calendar tools")

        return tools_list
