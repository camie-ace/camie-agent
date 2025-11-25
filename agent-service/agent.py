from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from dotenv import load_dotenv
import json
import logging
import asyncio
import signal

from livekit import agents, rtc
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import (
    noise_cancellation,
    silero,
)
from utils.config_fetcher import get_agent_config_from_room
from utils.plugin_factory import ModelFactory
from utils.config_processor import ConfigProcessor
from utils.session_monitors import SessionMonitors
from utils.tool_loader import ToolLoader
from utils.room_extractor import extract_room_name, extract_phone_number as extract_agent_conf_id
from utils.call_history import (
    start_call_recording,
    update_call_config,
    update_call_stage,
    end_call_recording
)
from assistant_factory import AgentConfig

# Configure logging
logger = logging.getLogger(__name__)

load_dotenv()


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
    def __init__(self,
                 instructions: str = "You are a helpful voice AI assistant.",
                 session_id: str = None,
                 ctx: Optional[agents.JobContext] = None,
                 agent_config: Optional[AgentConfig] = None,
                 raw_config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the Assistant agent.

        Args:
            instructions: Base instructions for the agent's behavior (used if agent_config not provided)
            session_id: Optional existing session ID for resuming a session
            ctx: Optional job context for the agent session
            agent_config: Optional pre-loaded AgentConfig object
            raw_config: Optional raw configuration dictionary from API
        """
        super().__init__(instructions=instructions)
        self._session_id = session_id
        self._interaction_stage = "greeting"
        self._agent_session: Optional[AgentSession] = None
        self._agent_config = agent_config  # Store pre-loaded config if provided
        self._raw_config = raw_config  # Store raw config for reference
        self._room_name: Optional[str] = None
        self._participant_context: Optional[Dict] = None
        self._audio_processor = noise_cancellation.BVC()
        self._ctx = ctx  # Store the job context

        # Initialize session monitors
        self._monitors = SessionMonitors(self)
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

        DEPRECATED: This method is no longer used in the refactored flow.
        The new entrypoint() uses create_assistant_with_config() factory function instead.
        Kept for backward compatibility with AbstractAgent interface.

        Args:
            ctx: The job context containing room and connection information
        """
        logger.warning(
            "initialize() called - this method is deprecated in the refactored flow")

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
        try:
            self._participant_context = ctx.room.remote_participants or (
                json.loads(ctx.room.metadata) if ctx.room.metadata else {}
            )
        except json.JSONDecodeError:
            logger.error(f"Failed to parse room metadata: {ctx.room.metadata}")
        logger.info(f"Existing participants: {ctx.room.remote_participants}")

        # Set up event listener
        ctx.room.on("participant_connected")(on_participant_join)

    async def handle_participant_connected(self, participant: rtc.RemoteParticipant) -> None:
        """Process new participant connection and initialize interaction

        DEPRECATED: This method is no longer used in the refactored flow.
        The new entrypoint() uses create_assistant_with_config() factory function instead.
        Kept for backward compatibility with AbstractAgent interface.

        Args:
            participant: The newly connected participant
        """
        logger.warning(
            "handle_participant_connected() called - this method is deprecated in the refactored flow")

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
            self._participant_context["call_type"] = context.get(
                "call_type", call_type)

            # For deprecated flow, we'd need raw_config here but don't have it
            # So we skip the recording initialization in deprecated path
            logger.warning(
                "Skipping recording initialization in deprecated path")

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

    async def _start_call_recording(self, config_id: str, interaction_type: str, raw_config: Dict[str, Any]) -> Optional[str]:
        """Initialize session recording and monitoring if not opted out

        Args:
            config_id: Unique identifier for agent configuration
            interaction_type: Type of interaction (web/voice)
            raw_config: Pre-fetched raw configuration dictionary from API

        Returns:
            str: The unique session identifier, or None if recording is disabled
        """
        try:
            # Skip recording if opt_out_sensitive_data is True
            if raw_config.get("opt_out_sensitive_data", False):
                logger.info(
                    f"Call recording disabled due to compliance settings: {raw_config.get('opt_out_sensitive_data')}")
                logger.info(
                    "No call history or sensitive data will be recorded for this session")
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
            logger.error(f"Error starting call recording: {str(e)}")
            # Default to not recording if there's an error
            return None

    async def _load_config(self) -> None:
        """Validate and finalize agent configuration (config should already be loaded)"""
        # If config was not pre-loaded, this is a fallback scenario
        if self._agent_config is None:
            logger.warning(
                "Agent config was not pre-loaded, fetching now (fallback mode)")
            raw_config = await get_agent_config_from_room(
                self._room_name,
                self._participant_context
            )
            self._raw_config = raw_config

            # Process and create AgentConfig using ConfigProcessor
            if raw_config:
                self._voice_activity_detection_control = raw_config.get(
                    'voice_activity_detection_control', 0.20)

            self._agent_config = AgentConfig(
                ctx=self._ctx,
                stt_config=raw_config if raw_config else {},
                tts_config=raw_config if raw_config else {},
                llm_config=raw_config if raw_config else {},
                instructions=raw_config.get(
                    "assistant_instruction",
                    "You are a helpful voice AI assistant."
                ) if raw_config else "You are a helpful voice AI assistant.",
                welcome_message=raw_config.get(
                    "static_message",
                    "Hello! How can I help you today?"
                ) if raw_config else "Hello! How can I help you today?",
                welcome_type=raw_config.get(
                    "welcome_message_type",
                    "human_initiates"
                ) if raw_config else "human_initiates",
                end_call_on_silence=raw_config.get(
                    "end_call_on_silence", False) if raw_config else False,
                silence_duration=raw_config.get(
                    "silence_duration", 60) if raw_config else 60,
                max_call_duration=raw_config.get(
                    "max_call_duration", 1800) if raw_config else 1800,
                tools=ConfigProcessor.prepare_tool_configs(
                    raw_config.get("tools", {}) if raw_config else {})
            )
        else:
            # Config was pre-loaded, just extract VAD control if needed
            if self._raw_config:
                self._voice_activity_detection_control = self._raw_config.get(
                    'voice_activity_detection_control', 0.20)
            logger.info("Using pre-loaded agent configuration")

        # Update session with configuration if recording is enabled
        if self._session_id and self._raw_config:
            await update_call_config(self._session_id, self._raw_config)
            logger.info(
                f"Updated call configuration for recorded session: {self._session_id}")
        else:
            logger.info(
                "Skipping call config update - recording disabled due to privacy settings")

        logger.info("Agent configuration validated", extra={
            "config": self._raw_config if self._raw_config else "default"
        })

    async def start_session(self) -> None:
        """Start the agent session"""
        await self._load_config()

        # Load tools based on configuration using ToolLoader
        # tools = await ToolLoader.load_tools(self._agent_config.tools)
        # tools_from_config = await ToolLoader.create_dynamic_tools([
        #     "fb0f2b86-a2bc-423b-a3af-3b9eee86675b"
        # ], "c00db557-5001-458d-8d97-78cf0af4d10a")
        logger.info(f"tools_list: {self._raw_config.get('tools_list', [])}")
        logger.info(f"workspace_id: {self._raw_config.get('workspace_id')}")
        logger.info(f"raw_config: {self._raw_config}")
        
        tools_from_config = await ToolLoader.create_dynamic_tools(self._raw_config.get("tools_list", []), self._raw_config.get("workspace_id"), self.ctx)
        logger.info(f"tools_from_config loaded: {len(tools_from_config)} tools")
        # Start call duration and silence monitors using SessionMonitors
        self._monitors.start_monitoring(
            max_call_duration=self._agent_config.max_call_duration,
            enable_silence_detection=self._agent_config.end_call_on_silence,
            silence_duration=self._agent_config.silence_duration
        )

        # Create model components
        stt = ModelFactory.create_stt(self._agent_config.stt_config)
        llm = ModelFactory.create_llm(self._agent_config.llm_config)
        tts = ModelFactory.create_tts(self._agent_config.tts_config)

        logger.info(f"tts: {tts}")
        logger.info(f"llm: {llm}")
        logger.info(f"stt: {stt}")

        self._agent_session = AgentSession(
            stt=stt,
            llm=llm,
            tts=tts,
            vad=silero.VAD.load(
                min_silence_duration=self._voice_activity_detection_control or 0.05),
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

        await self.update_tools(tools_from_config)

        # Register voice activity handler if we're using silence detection
        if self._agent_config.end_call_on_silence:
            self._monitors.setup_voice_activity_handler(self._agent_session)

        # Handle welcome message based on welcome_message_type
        if self._agent_config.welcome_type == "ai_initiates":
            # AI initiates with dynamic response
            await self._agent_session.generate_reply(
                instructions="Greet the user naturally and ask how you can help them today."
            )
        elif self._agent_config.welcome_type == "ai_static":
            # AI initiates with static message
            await self._agent_session.say(self._agent_config.welcome_message)
         
        # For "human_initiates", we don't send any welcome message and wait for the user to speak first

    async def end_session(self, reason: str = None) -> None:
        """End the agent session and terminate the call completely"""
        logger.info(f"Ending session with reason: {reason}")

        # Cancel monitoring tasks using SessionMonitors
        await self._monitors.cancel_all()

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
            logger.info(
                "Session ended (no recording to finalize - disabled due to compliance settings)")

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
    # Import here to avoid circular dependency
    from assistant_factory import create_assistant_with_config

    assistant = None
    try:
        # Connect to the room first
        await ctx.connect()
        room_name = extract_room_name(ctx)
        logger.info(f"Connected to room: {room_name}")

        # Parse initial room metadata
        try:
            participant_context = ctx.room.remote_participants or (
                json.loads(ctx.room.metadata) if ctx.room.metadata else {}
            )
        except json.JSONDecodeError:
            logger.error(f"Failed to parse room metadata: {ctx.room.metadata}")
            participant_context = {}

        logger.info(
            f"Initial participants in room: {ctx.room.remote_participants}")

        # Check if participant is already in the room (web calls)
        participant = None
        if ctx.room.remote_participants:
            # Get the first remote participant (usually there's only one)
            participant = list(ctx.room.remote_participants.values())[0]
            logger.info(f"Participant already in room: {participant.identity}")
        else:
            # Wait for participant to connect (telephony calls)
            participant_connected = asyncio.Event()
            participant_ref = {"participant": None}

            def on_participant_join(participant: rtc.RemoteParticipant):
                logger.info(f"Participant joined: {participant.identity}")
                participant_ref["participant"] = participant
                participant_connected.set()

            # Register participant connection handler
            ctx.room.on("participant_connected")(on_participant_join)

            # Wait for participant with timeout (10 seconds)
            try:
                await asyncio.wait_for(participant_connected.wait(), timeout=10.0)
                participant = participant_ref["participant"]
                logger.info(f"Participant connected: {participant.identity}")
            except asyncio.TimeoutError:
                logger.error("Timeout waiting for participant to connect")
                raise Exception(
                    "No participant connected within timeout period")

        # Parse participant metadata
        try:
            if participant.metadata:
                context = json.loads(participant.metadata)
                participant_context.update(context)
                logger.info(f"Parsed participant metadata: {context}")
            # Also check if identity contains metadata (LiveKit sometimes puts it there)
            elif participant.identity:
                try:
                    context = json.loads(participant.identity)
                    participant_context.update(context)
                    logger.info(
                        f"Parsed participant identity as metadata: {context}")
                except (json.JSONDecodeError, TypeError):
                    # Identity is just a regular string, not JSON
                    logger.info(
                        f"Participant identity is not JSON: {participant.identity}")
        except json.JSONDecodeError:
            logger.error(
                f"Failed to parse participant metadata: {participant.metadata}")

        # Create assistant with configuration from API (deferred instantiation)
        assistant = await create_assistant_with_config(
            ctx=ctx,
            room_name=room_name,
            participant=participant,
            participant_context=participant_context
        )

        logger.info("Assistant instantiated with API configuration")

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
