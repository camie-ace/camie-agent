"""
Configuration processor for agent settings.

This module handles the preparation and transformation of raw configuration
data into structured configuration objects for STT, TTS, LLM, and tools.
"""

from typing import Dict, Any
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolConfig:
    """Data class to hold tool configuration"""
    enabled: bool
    url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ConfigProcessor:
    """Processes and prepares agent configuration from raw API responses"""

    @staticmethod
    def prepare_stt_config(config: Dict) -> Dict:
        """Prepare STT configuration

        Args:
            config: Raw configuration dictionary from the config service

        Returns:
            Dict containing structured STT configuration
        """
        stt_config = {
            "provider": config.get("transcription_provider", "deepgram"),
            "model": config.get("transcription_provider_model", "nova-2"),
            "language": config.get("agent_language", "en-US")
        }
        logger.info(f"Using STT provider: {stt_config['provider']}")
        return stt_config

    @staticmethod
    def prepare_tts_config(config: Dict) -> Dict:
        """Prepare TTS configuration

        Args:
            config: Raw configuration dictionary from the config service

        Returns:
            Dict containing structured TTS configuration
        """
        tts_config = {
            "provider": config.get("voice_provider", "cartesia"),
            "model": config.get("voice_provider_model", "sonic-2"),
            "voice": config.get("voice"),
            "custom_voice_id": config.get("custom_voice_id"),
            "speed": float(config.get("voice_speed", 1.0)),
            "stability": int(config.get("stability", 75)) / 100,
            "similarity_boost": int(config.get("clarity_similarity", 85)) / 100,
            "voice_improvement": bool(config.get("voice_improvement", True)),
            "language": config.get("agent_language", "en-US")
        }
        logger.info(
            f"Using TTS provider: {tts_config['provider']} with voice: {tts_config['voice']}")
        return tts_config

    @staticmethod
    def prepare_llm_config(config: Dict) -> Dict:
        """Prepare LLM configuration

        Args:
            config: Raw configuration dictionary from the config service

        Returns:
            Dict containing structured LLM configuration
        """
        llm_config = {
            "provider": config.get("llm", "openai"),
            "model": config.get("llm_model", "gpt-4"),
            "temperature": 0.7  # Default temperature if not specified
        }

        logger.info(
            f"Using LLM provider: {llm_config['provider']} with model: {llm_config['model']}")
        return llm_config

    @staticmethod
    def prepare_tool_configs(tools_config: Dict[str, Any]) -> Dict[str, ToolConfig]:
        """
        Process raw tool configuration into structured ToolConfig objects

        Args:
            tools_config: Raw tool configuration from API

        Returns:
            Dictionary mapping tool names to their configurations
        """
        result = {}

        # Default tool configuration (all disabled)
        default_tools = {
            "knowledge_base": False,
            "sms": False,
            "calendar": False,
            "email": False
        }

        # For backward compatibility, handle legacy boolean format
        for tool_name, default in default_tools.items():
            # Check if the tool exists in config
            tool_config = tools_config.get(tool_name, default)

            # If it's just a boolean, convert to ToolConfig
            if isinstance(tool_config, bool):
                result[tool_name] = ToolConfig(
                    enabled=tool_config,
                    url=None,
                    metadata=None
                )
            # If it's a dictionary, extract the structured data
            elif isinstance(tool_config, dict):
                result[tool_name] = ToolConfig(
                    enabled=tool_config.get("enabled", False),
                    url=tool_config.get("url"),
                    metadata=tool_config.get("metadata", {})
                )
            # Otherwise, default to disabled
            else:
                result[tool_name] = ToolConfig(
                    enabled=False,
                    url=None,
                    metadata=None
                )

        return result
