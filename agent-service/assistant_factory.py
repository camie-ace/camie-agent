"""
Factory module for creating configured Assistant instances.

This module provides a factory function that fetches configuration from the API,
creates an AgentConfig, and instantiates an Assistant with proper settings.
"""

import logging
from typing import Dict, Any
from livekit import agents, rtc
from livekit.plugins import noise_cancellation
from dataclasses import dataclass

from utils.config_fetcher import get_agent_config_from_room
from utils.config_processor import ToolConfig
from utils.call_history import start_call_recording
from utils.room_extractor import extract_phone_number as extract_agent_conf_id

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Data class to hold agent configuration"""
    ctx: agents.JobContext
    stt_config: Dict[str, Any]
    tts_config: Dict[str, Any]
    llm_config: Dict[str, Any]
    instructions: str
    welcome_message: str
    welcome_type: str
    end_call_on_silence: bool
    silence_duration: int
    max_call_duration: int
    tools: Dict[str, ToolConfig]


async def create_assistant_with_config(
    ctx: agents.JobContext,
    room_name: str,
    participant: rtc.RemoteParticipant,
    participant_context: Dict[str, Any]
):
    """Factory function to create Assistant with configuration fetched from API.

    This function:
    1. Determines call type and config ID from participant
    2. Fetches agent configuration from API
    3. Checks opt_out_sensitive_data for recording decision
    4. Creates AgentConfig with API data or defaults
    5. Instantiates and returns Assistant with proper configuration

    Args:
        ctx: Job context for the agent session
        room_name: Name of the LiveKit room
        participant: The connected participant
        participant_context: Parsed participant metadata

    Returns:
        Assistant: Fully configured Assistant instance
    """
    # Import here to avoid circular dependency
    from agent import Assistant

    logger.info(f"Creating assistant with configuration for room: {room_name}")

    # Determine call type and config ID based on participant
    if participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP:
        config_id = extract_agent_conf_id(room_name)
        logger.info(f"SIP call detected - config ID: {config_id}")

        # Check for direction or call_type in participant context
        # Prefer 'direction' field, but fall back to 'call_type' if present
        if "direction" in participant_context:
            call_type = participant_context["direction"]
            logger.info(
                f"Using direction from participant context: {call_type}")
        elif "call_type" in participant_context:
            call_type = participant_context["call_type"]
            participant_context["direction"] = call_type
            logger.info(
                f"Using call_type from participant context: {call_type}")
        else:
            call_type = "inbound"
            participant_context["direction"] = "inbound"
            logger.info(
                "No direction or call_type in participant context, defaulting to inbound")
    else:
        call_type = "web"
        config_id = participant.identity
        logger.info(f"Web call detected - config ID: {config_id}")
        # For web calls, also set direction if not present
        if "direction" not in participant_context:
            participant_context["direction"] = "inbound"

    # Add call type to participant context for backward compatibility
    participant_context["call_type"] = call_type

    # Fetch configuration from API
    try:
        raw_config = await get_agent_config_from_room(room_name, participant_context)
        logger.info(f"Configuration fetched from API: {bool(raw_config)}")
    except Exception as e:
        logger.error(f"Error fetching configuration from API: {str(e)}")
        raw_config = {}

    # Determine if recording should be enabled based on opt_out setting
    opt_out_recording = raw_config.get("opt_out_sensitive_data", False)
    session_id = None

    if not opt_out_recording:
        try:
            session_id = await start_call_recording(
                phone_number=config_id,
                room_name=room_name,
                call_type=call_type
            )
            logger.info(f"Call recording initialized: {session_id}")
        except Exception as e:
            logger.error(f"Error starting call recording: {str(e)}")
            session_id = None
    else:
        logger.info("Call recording disabled due to compliance settings")

    # Extract VAD control from raw config
    voice_activity_detection_control = raw_config.get(
        'voice_activity_detection_control', 0.20) if raw_config else 0.20

    # Create AgentConfig from raw config or use defaults
    # Pass raw config directly to plugin factory
    from utils.config_processor import ConfigProcessor

    if raw_config:
        agent_config = AgentConfig(
            ctx=ctx,
            stt_config=raw_config,  # Pass raw config to plugin factory
            tts_config=raw_config,  # Pass raw config to plugin factory
            llm_config=raw_config,  # Pass raw config to plugin factory
            instructions=raw_config.get(
                "assistant_instruction",
                "You are a helpful voice AI assistant."
            ),
            welcome_message=raw_config.get(
                "static_message",
                "Hello! How can I help you today?"
            ),
            welcome_type=raw_config.get(
                "welcome_message_type",
                "human_initiates"
            ),
            end_call_on_silence=raw_config.get("end_call_on_silence", False),
            silence_duration=raw_config.get("silence_duration", 60),
            max_call_duration=raw_config.get("max_call_duration", 1800),
            tools=ConfigProcessor.prepare_tool_configs(
                raw_config.get("tools", {}))
        )
        logger.info("AgentConfig created from API configuration")
    else:
        # Use default configuration with empty dict (plugin factory will use defaults)
        agent_config = AgentConfig(
            ctx=ctx,
            stt_config={},  # Plugin factory will use defaults
            tts_config={},  # Plugin factory will use defaults
            llm_config={},  # Plugin factory will use defaults
            instructions="You are a helpful voice AI assistant.",
            welcome_message="Hello! How can I help you today?",
            welcome_type="human_initiates",
            end_call_on_silence=False,
            silence_duration=60,
            max_call_duration=1800,
            tools=ConfigProcessor.prepare_tool_configs({})
        )
        logger.info(
            "AgentConfig created with default values (API returned no config)")

    # Configure audio processor based on participant type
    audio_processor = (noise_cancellation.BVCTelephony()
                       if participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                       else noise_cancellation.BVC())

    # Create Assistant instance with pre-loaded configuration
    assistant = Assistant(
        instructions=agent_config.instructions,
        session_id=session_id,
        ctx=ctx,
        agent_config=agent_config,
        raw_config=raw_config
    )

    # Set instance variables that were determined during config fetch
    assistant._room_name = room_name
    assistant._participant_context = participant_context
    assistant._audio_processor = audio_processor
    assistant._voice_activity_detection_control = voice_activity_detection_control

    logger.info(
        f"Assistant created successfully with config-driven instructions")
    return assistant
