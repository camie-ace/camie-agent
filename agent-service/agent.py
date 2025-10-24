from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Callable
from abc import ABC, abstractmethod
from dotenv import load_dotenv
import json
import logging
import asyncio
import signal
import os

from livekit import agents, rtc
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import (
    noise_cancellation,
    silero,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from utils.config_fetcher import get_agent_config_from_room
from utils.model_factory import ModelFactory

from utils.room_extractor import extract_room_name, extract_phone_number as extract_agent_conf_id
from utils.call_history import (
    start_call_recording,
    update_call_config,
    update_call_stage,
    end_call_recording
)
from utils.business_tools import get_tool_by_name

# Configure logging
logger = logging.getLogger(__name__)

load_dotenv()


@dataclass
class ToolConfig:
    """Data class to hold tool configuration"""
    enabled: bool
    url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


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


class AbstractAgent(Agent, ABC):
    """Abstract base class for all agents"""

    @abstractmethod
    async def initialize(self, ctx: agents.JobContext) -> None:
        """Initialize the agent with context"""
        pass

    @abstractmethod
    async def handle_participant_connected(self, participant: rtc.RemoteParticipant) -> None:
        """Handle participant connection"""
        pass

    @abstractmethod
    async def start_session(self) -> None:
        """Start the agent session"""
        pass

    @abstractmethod
    async def end_session(self, reason: str = None) -> None:
        """End the agent session"""
        pass


class Assistant(AbstractAgent):
    def __init__(self, instructions: str = "You are a helpful voice AI assistant.", session_id: str = None, ctx: Optional[agents.JobContext] = None) -> None:
        """Initialize the Assistant agent.

        Args:
            instructions: Base instructions for the agent's behavior
            session_id: Optional existing session ID for resuming a session
            ctx: Optional job context for the agent session
        """
        super().__init__(instructions=instructions)
        self._session_id = session_id
        self._interaction_stage = "greeting"
        self._agent_session: Optional[AgentSession] = None
        self._agent_config: Optional[AgentConfig] = None
        self._room_name: Optional[str] = None
        self._participant_context: Optional[Dict] = None
        self._audio_processor = noise_cancellation.BVC()
        self._tools: List[Callable] = []
        self._ctx = ctx  # Store the job context

        # Session monitoring
        self._call_duration_task: Optional[asyncio.Task] = None
        self._silence_monitor_task: Optional[asyncio.Task] = None
        self._last_voice_activity_time = asyncio.Event()
        self._voice_activity_detection_control = None
        self._interruption_sensitivity_control = None

    @property
    def interaction_stage(self) -> str:
        """Get the current stage of the conversation interaction"""
        return self._interaction_stage

    @property
    def session_id(self) -> Optional[str]:
        """Get the current session ID"""
        return self._session_id

    @property
    def ctx(self) -> Optional[agents.JobContext]:
        """Get the job context"""
        return self._ctx

    async def update_interaction_stage(self, stage: str) -> None:
        """Update and record the current interaction stage

        Args:
            stage: The new stage of the conversation
        """
        self._interaction_stage = stage
        # Only update call stage if recording is enabled (session_id exists)
        if self._session_id:
            await update_call_stage(self._session_id, stage)
            logger.info(
                f"Session {self._session_id}: Stage updated to {stage}")
        else:
            logger.info(f"Stage updated to {stage} (recording disabled)")

    async def initialize(self, ctx: agents.JobContext) -> None:
        """Initialize the agent with the given context

        Args:
            ctx: The job context containing room and connection information
        """
        # Store the job context
        self._ctx = ctx

        # Establish connection
        await ctx.connect()

        # Initialize room context
        self._room_name = extract_room_name(ctx)
        logger.info(f"Initializing agent for room: {self._room_name}")

        # Register participant handler
        def on_participant_join(participant: rtc.RemoteParticipant):
            asyncio.create_task(self.handle_participant_connected(participant))

        # Log initial room state
        logger.info(f"Room context: {ctx.room}")
        logger.info(f"Existing participants: {ctx.room.remote_participants}")

        # Set up event listener
        ctx.room.on("participant_connected")(on_participant_join)

    async def handle_participant_connected(self, participant: rtc.RemoteParticipant) -> None:
        """Process new participant connection and initialize interaction

        Args:
            participant: The newly connected participant
        """
        # Log comprehensive participant information
        logger.info("New participant connection:", extra={
            "participant_details": str(participant),
            "connection_type": participant.kind,
            "identity": participant.identity,
            "metadata": participant.metadata
        })

        try:
            # Extract participant context
            context = self._parse_participant_metadata(participant)

            # Determine interaction type and configuration ID
            if participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP:
                call_type = "inbound"
                config_id = extract_agent_conf_id(self._room_name)
                logger.info(f"Voice call configuration ID: {config_id}")
            else:
                call_type = "web"
                config_id = participant.identity
                logger.info("Web interaction initialized")

            # Configure audio processing based on participant type
            self._audio_processor = (noise_cancellation.BVCTelephony()
                                     if participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                                     else noise_cancellation.BVC())

            # Update interaction context
            context["call_type"] = context.get("call_type", call_type)
            self._participant_context = context

            # Initialize session recording if not opted out
            self._session_id = await self._start_call_recording(config_id, call_type)
            logger.info(f"Call type: {call_type}")

            if self._session_id is None:
                logger.info(
                    "Session recording disabled - no call history will be saved")
        except Exception as e:
            logger.error(f"Error handling participant connection: {str(e)}")
            self._participant_context = {}
            return

    def _parse_participant_metadata(self, participant: rtc.RemoteParticipant) -> Dict:
        """Extract and parse participant metadata

        Args:
            participant: The participant whose metadata needs to be parsed

        Returns:
            Dict containing parsed metadata or empty dict if parsing fails
        """
        try:
            if participant.metadata:
                return json.loads(participant.metadata)
        except json.JSONDecodeError:
            logger.error(
                f"Failed to parse participant metadata: {participant.metadata}")
        return {}

    async def _start_call_recording(self, config_id: str, interaction_type: str) -> Optional[str]:
        """Initialize session recording and monitoring if not opted out

        Args:
            config_id: Unique identifier for agent configuration
            interaction_type: Type of interaction (web/voice)

        Returns:
            str: The unique session identifier, or None if recording is disabled
        """
        # First, check if we need to get the configuration to check opt_out_sensitive_data
        try:
            # Fetch raw config to check opt_out_sensitive_data setting
            raw_config = await get_agent_config_from_room(
                self._room_name,
                self._participant_context
            )

            # Skip recording if opt_out_sensitive_data is True
            if raw_config.get("opt_out_sensitive_data", False):
                logger.info(
                    f"Call recording disabled due to compliance settings: {raw_config.get('opt_out_sensitive_data')}")
                logger.info("No call history or sensitive data will be recorded for this session")
                return None

            # Proceed with recording since opt_out_sensitive_data is False or not set
            session_id = await start_call_recording(
                phone_number=config_id,
                room_name=self._room_name,
                call_type=interaction_type
            )
            logger.info(f"Initialized session recording: {session_id}")
            return session_id

        except Exception as e:
            logger.error(f"Error checking recording opt-out status: {str(e)}")
            # Default to not recording if there's an error
            return None

    async def _load_config(self) -> None:
        """Load and initialize agent configuration"""
        # Fetch configuration based on room and context
        raw_config = await get_agent_config_from_room(
            self._room_name,
            self._participant_context
        )

        # Update session with configuration if recording is enabled
        # Only update call config if recording is active (session_id exists)
        if self._session_id:
            await update_call_config(self._session_id, raw_config)
            logger.info(f"Updated call configuration for recorded session: {self._session_id}")
        else:
            logger.info("Skipping call config update - recording disabled due to privacy settings")

        logger.info("Agent configuration loaded", extra={
            "config": raw_config
        })

        if (raw_config):
            self._voice_activity_detection_control = raw_config.get(
                'voice_activity_detection_control', 0.20)

        # Initialize processed configuration
        self._agent_config = AgentConfig(
            ctx=self._ctx,
            stt_config=self._prepare_stt_config(raw_config),
            tts_config=self._prepare_tts_config(raw_config),
            llm_config=self._prepare_llm_config(raw_config),
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
                "user_initiates"
            ),
            end_call_on_silence=raw_config.get("end_call_on_silence", False),
            silence_duration=raw_config.get("silence_duration", 60),
            max_call_duration=raw_config.get("max_call_duration", 1800),
            tools=self._prepare_tool_configs(raw_config.get("tools", {}))
        )

    def _prepare_stt_config(self, config: Dict) -> Dict:
        """Prepare STT configuration"""
        stt_config = {
            "provider": config.get("transcription_provider", "deepgram"),
            "language": config.get("agent_language", "en-US")
        }
        logger.info(f"Using STT provider: {stt_config['provider']}")
        return stt_config

    def _prepare_tts_config(self, config: Dict) -> Dict:
        """Prepare TTS configuration"""
        tts_config = {
            "provider": config.get("voice_provider", None),
            "voice": config.get("voice", None),
            "custom_voice_id": config.get("custom_voice_id"),
            "speed": config.get("voice_speed", 1),
            "stability": config.get("stability", 75),
            "clarity_similarity": config.get("clarity_similarity", 80),
            "voice_improvement": config.get("voice_improvement", True),
            "language": config.get("agent_language", None)
        }
        logger.info(
            f"Using TTS provider: {tts_config['provider']} with voice: {tts_config['voice']}")
        return tts_config

    def _prepare_llm_config(self, config: Dict) -> Dict:
        """Prepare LLM configuration"""
        return {}

    def _prepare_tool_configs(self, tools_config: Dict[str, Any]) -> Dict[str, ToolConfig]:
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

    async def _load_tools(self) -> List[Callable]:
        """
        Load tools based on agent configuration

        Returns:
            List of callable tool functions
        """
        tools_list = []
        if not self._agent_config:
            return tools_list

        # Get tool configuration
        tool_configs = self._agent_config.tools

        # Load each enabled tool with its configuration
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

    async def start_session(self) -> None:
        """Start the agent session"""
        await self._load_config()

        # Load tools based on configuration
        tools = await self._load_tools()

        # Start call duration and silence monitors if configured
        if self._agent_config.max_call_duration > 0:
            self._call_duration_task = asyncio.create_task(
                self._monitor_call_duration(
                    self._agent_config.max_call_duration)
            )

        if self._agent_config.end_call_on_silence and self._agent_config.silence_duration > 0:
            self._silence_monitor_task = asyncio.create_task(
                self._monitor_silence(self._agent_config.silence_duration)
            )

        # Create model components
        stt = ModelFactory.create_stt(self._agent_config.stt_config)
        llm = ModelFactory.create_llm(self._agent_config.llm_config)
        tts = ModelFactory.create_tts(self._agent_config.tts_config)

        self._agent_session = AgentSession(
            stt=stt,
            llm=llm,
            tts=tts,
            vad=silero.VAD.load(
                min_silence_duration=self._voice_activity_detection_control or 0.20),
            # turn_detection=MultilingualModel(),
            allow_interruptions=True,
        )

        # Start session
        await self._agent_session.start(
            room=self._ctx.room,
            agent=self,
            room_input_options=RoomInputOptions(
                noise_cancellation=self._audio_processor,
            ),
        )

        # Reset the voice activity tracker whenever we detect speech
        def on_voice_activity(is_speaking: bool):
            if is_speaking:
                self._last_voice_activity_time.set()
                self._last_voice_activity_time.clear()

        # Register voice activity handler if we're using silence detection
        if self._agent_config.end_call_on_silence:
            self._agent_session.on("voice_activity")(on_voice_activity)

        # Generate welcome message
        await self._agent_session.generate_reply(
            instructions=f"Greet the user with: {self._agent_config.welcome_message}"
        )

    async def _monitor_call_duration(self, max_duration_seconds: int) -> None:
        """
        Monitor and end call after max duration

        Args:
            max_duration_seconds: Maximum call duration in seconds
        """
        try:
            logger.info(
                f"Call duration monitor started: {max_duration_seconds}s maximum")
            await asyncio.sleep(max_duration_seconds)

            if self._agent_session:
                logger.info(
                    "Call duration limit reached - sending farewell message")
                # Inform user that call duration limit reached
                await self._agent_session.generate_reply(
                    instructions="Inform the user that the maximum call duration has been reached and say goodbye politely.",
                    allow_interruptions=False
                )

                # Allow time for the goodbye message to be spoken and heard
                logger.info("Waiting for farewell message to complete")
                # Increased time to ensure message is fully delivered
                await asyncio.sleep(8)

                # End the call
                logger.info("Ending call due to maximum duration exceeded")
                await self.end_session("max_duration_exceeded")

        except asyncio.CancelledError:
            logger.info("Call duration monitor cancelled")
        except Exception as e:
            logger.exception(f"Error in call duration monitor: {str(e)}")

    async def _monitor_silence(self, silence_duration_seconds: int) -> None:
        """
        Monitor for silence and end call after specified duration

        Args:
            silence_duration_seconds: Maximum silence duration in seconds
        """
        try:
            logger.info(
                f"Silence monitor started: {silence_duration_seconds}s threshold")

            while True:
                # Wait for the silence duration
                try:
                    # Wait for voice activity or timeout
                    await asyncio.wait_for(
                        self._last_voice_activity_time.wait(),
                        timeout=silence_duration_seconds
                    )
                    # If we reach here, there was voice activity, so reset and continue monitoring
                    continue
                except asyncio.TimeoutError:
                    # No voice activity detected within timeout period
                    if self._agent_session:
                        logger.info(
                            "Silence timeout reached - sending farewell message")
                        # Inform user about silence timeout
                        await self._agent_session.generate_reply(
                            instructions="Inform the user that due to lack of activity, you need to end the call, and say goodbye politely.",
                            allow_interruptions=False
                        )

                        # Allow time for the goodbye message to be spoken and heard
                        logger.info("Waiting for farewell message to complete")
                        # Increased time to ensure message is fully delivered
                        await asyncio.sleep(8)

                        # End the call
                        logger.info("Ending call due to silence timeout")
                        await self.end_session("silence_timeout")
                        break

        except asyncio.CancelledError:
            logger.info("Silence monitor cancelled")
        except Exception as e:
            logger.exception(f"Error in silence monitor: {str(e)}")

    async def end_session(self, reason: str = None) -> None:
        """End the agent session and terminate the call completely"""
        logger.info(f"Ending session with reason: {reason}")

        # Cancel monitoring tasks
        if self._call_duration_task and not self._call_duration_task.done():
            self._call_duration_task.cancel()
            logger.info("Cancelled call duration monitoring task")

        if self._silence_monitor_task and not self._silence_monitor_task.done():
            self._silence_monitor_task.cancel()
            logger.info("Cancelled silence monitoring task")

        # Stop the agent session
        if self._agent_session:
            logger.info("Stopping agent session")
            await self._agent_session.aclose()
            self._agent_session = None

        # Record the call ending if recording was enabled
        if self._session_id:
            logger.info(
                f"Recording call completion for session: {self._session_id}")
            try:
                if reason:
                    await end_call_recording(
                        call_id=self._session_id,
                        status="dropped",
                        reason=reason
                    )
                else:
                    await end_call_recording(
                        call_id=self._session_id,
                        status="completed",
                        outcomes={
                            "final_stage": self._interaction_stage,
                            "successful": True
                        }
                    )
                logger.info("Call recording completed successfully")
            except Exception as e:
                logger.error(f"Error finalizing call recording: {str(e)}")
        else:
            logger.info("Session ended (no recording to finalize - disabled due to compliance settings)")

        # Terminate the call by disconnecting from the room
        await self._terminate_call(reason)

    async def _terminate_call(self, reason: str = None) -> None:
        """Terminate the call by disconnecting from the room and cleaning up resources"""
        try:
            if self._ctx and self._ctx.room:
                logger.info(
                    f"Terminating call - disconnecting from room: {self._room_name}")

                # Disconnect the local participant from the room
                await self._ctx.room.disconnect()
                logger.info("Successfully disconnected from room")

                # Optional: Add a small delay to ensure cleanup completes
                await asyncio.sleep(1)

            else:
                logger.warning(
                    "No room context available for call termination")

        except Exception as e:
            logger.error(f"Error during call termination: {str(e)}")
            # Continue with cleanup even if room disconnection fails

        logger.info(
            f"Call terminated successfully. Reason: {reason or 'normal completion'}")


async def entrypoint(ctx: agents.JobContext):
    """Entry point for the agent service"""
    assistant = None
    try:
        # Create and initialize the assistant with the context
        assistant = Assistant(ctx=ctx)
        await assistant.initialize(ctx)

        # Set up signal handlers for graceful shutdown
        loop = asyncio.get_event_loop()

        def handle_signal(sig, frame):
            logger.info(f"Received signal {sig}, ending call")
            asyncio.create_task(assistant.end_session("system_interrupt"))

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda s=sig: handle_signal(s, None))

        # Start the assistant session
        await assistant.start_session()

    except Exception as e:
        logger.error(f"Error in agent entrypoint: {e}")
        if assistant and assistant.session_id:
            await assistant.end_session(str(e))
        raise


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
