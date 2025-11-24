"""
Tool loader for agent business tools.

This module manages the loading and configuration of business tools
such as knowledge base, SMS, calendar integrations, etc.
"""

import os
import logging
from typing import List, Callable, Dict
from utils.config_processor import ToolConfig
from utils.business_tools import get_tool_by_name, create_tool_hanler
from livekit.agents import function_tool
from utils.api_client import get_tools_schema

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


    # this method will handle the parameters for fields that have static parameters
    def _augment_parameters_for_type(params: Dict[str, any], tool_type: str) -> Dict[str, any]:
        props = params.get("properties", {}) or {}
        required = params.get("required", []) or []
        if tool_type == ToolType.QUERY.value:
            props["query"] = {"type": "string", "description": "The query to search for"}
            required = required + ["query"]

        params["properties"] = props
        params["required"] = required

        return params

    def _parse_schema(schema: Dict[str, any], tool_type: str) -> Dict[str, any]:
        parsed_tool = None
        tool_func = schema.get("function")
        if tool_func:
            params = tool_func.get("parameters", {}) or {}
            props = params.get("properties", {}) or {}
            required = params.get("required", []) or []
            params["properties"] = props
            params["required"] = required
            params = ToolLoader._augment_parameters_for_type(params, tool_type)
            parsed_tool = {
                "name": tool_func.get("name", ""),
                "description": tool_func.get("description", ""),
                "parameters": params
            }
        return parsed_tool

    
    @staticmethod
    async def create_dynamic_tools(tool_configs: list[str], workspace_id: str) -> List[Callable]:
        """
        Create dynamic tools based on configuration

        Args:
            tool_configs: Array of tool configuration  uuid strings

        Returns:
            List of callable tool functions
        """
        tools_list = []
        list_of_tools_schema = await get_tools_schema(tool_configs, workspace_id)

        if (list_of_tools_schema.get("error")):
            return tools_list
        
        for tool_schema in list_of_tools_schema.get("tools", []):
            parsed_tool = ToolLoader._parse_schema(tool_schema.get("config"), tool_schema.get("type"))
            if parsed_tool:
                tool_handler = create_tool_hanler(tool_schema)
                if tool_handler:
                    tools_list.append(function_tool(tool_handler, raw_schema=parsed_tool))
                
        return tools_list