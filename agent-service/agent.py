from dataclasses import dataclass
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from dotenv import load_dotenv
import json
import logging
import asyncio
import signal

from livekit import agents, rtc
from livekit.agents import AgentSession, Agent, RoomInputOptions, JobProcess
from livekit.plugins import (
    noise_cancellation,
    silero,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from utils.config_fetcher import get_agent_config_from_room
from utils.model_factory import ModelFactory
# TODO: Rename this function in the module
from utils.room_extractor import extract_room_name, extract_phone_number as extract_agent_conf_id
from utils.call_history import (
    start_call_recording,
    update_call_config,
    update_call_stage,
    end_call_recording
)

# Configure logging
logger = logging.getLogger(__name__)

load_dotenv()


@dataclass
class AgentConfig:
    """Data class to hold agent configuration"""
    stt_config: Dict[str, Any]
    tts_config: Dict[str, Any]
    llm_config: Dict[str, Any]
    instructions: str
    welcome_message: str
    welcome_type: str


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
    def __init__(self, instructions: str = "You are a helpful voice AI assistant.", call_id: str = None) -> None:
        super().__init__(instructions=instructions)
        self._call_id = call_id
        self._current_stage = "greeting"
        self._session: Optional[AgentSession] = None
        self._config: Optional[AgentConfig] = None
        self._room_name: Optional[str] = None
        self._participant_metadata: Optional[Dict] = None
        self._noise_cancellation = noise_cancellation.BVC()

    @property
    def current_stage(self) -> str:
        """Get the current stage of the conversation"""
        return self._current_stage

    @property
    def call_id(self) -> Optional[str]:
        """Get the call ID"""
        return self._call_id

    async def on_stage_update(self, stage: str) -> None:
        """Handle stage updates and record them in call history"""
        self._current_stage = stage
        if self._call_id:
            await update_call_stage(self._call_id, stage)
            logger.info(f"Call {self._call_id}: Stage updated to {stage}")

    async def initialize(self, ctx: agents.JobContext) -> None:
        """Initialize the agent with context"""
        await ctx.connect()
        self._room_name = extract_room_name(ctx)
        logger.info(f"Processing job request for room: {self._room_name}")

        # Set up participant connection handler
        def on_participant_connected(participant: rtc.RemoteParticipant):
            asyncio.create_task(self.handle_participant_connected(participant))
        logger.info(f"Participant connected: {ctx.room}")
        logger.info(
            f"remote Participant connected: {ctx.room.remote_participants}")
        ctx.room.on("participant_connected")(on_participant_connected)

    async def handle_participant_connected(self, participant: rtc.RemoteParticipant) -> None:
        """Handle participant connection events"""
        logger.info(f"Participant connected with details: {participant}")
        logger.info(f"Participant kind: {participant.kind}")
        logger.info(f"Participant identity: {participant.identity}")
        logger.info(f"Participant metadata: {participant.metadata}")

        try:
            # Parse metadata regardless of participant type
            metadata = json.loads(
                participant.metadata) if participant.metadata else {}

            # Handle different participant types
            if participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP:
                # Handle SIP call
                agent_conf_id = extract_agent_conf_id(self._room_name)
                logger.info(f"SIP call with agent config ID: {agent_conf_id}")
                call_type = "inbound"  # Default for SIP calls
            else:
                # Handle web call
                logger.info("Web call participant connected")
                call_type = "web"
                agent_conf_id = participant.identity
            # Override call_type if specified in metadata
            call_type = metadata.get('call_type', call_type)
            self._participant_metadata = metadata

            # Set noise cancellation based on call type
            if participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP:
                self._noise_cancellation = noise_cancellation.BVCTelephony()
            else:
                self._noise_cancellation = noise_cancellation.BVC()

            logger.info(f"Call type: {call_type}")

            # Start call recording
            self._call_id = await self._start_call_recording(agent_conf_id, call_type)

        except json.JSONDecodeError:
            logger.error(
                f"Failed to parse participant metadata: {participant.metadata}")
            # Still proceed with default values
            self._participant_metadata = {}

    async def _start_call_recording(self, agent_conf_id: str, call_type: str) -> str:
        """Start call recording and return call_id"""
        call_id = await start_call_recording(
            agent_conf_id=agent_conf_id,  # Using the new parameter name
            room_name=self._room_name,
            call_type=call_type
        )
        logger.info(f"Started call recording with ID: {call_id}")
        return call_id

    async def _load_config(self) -> None:
        """Load and process agent configuration"""
        agent_config = await get_agent_config_from_room(self._room_name, self._participant_metadata)
        await update_call_config(self._call_id, agent_config)
        logger.info(
            f"Using agent configuration: {json.dumps(agent_config, indent=2)}")

        # Process configuration
        self._config = AgentConfig(
            stt_config=self._prepare_stt_config(agent_config),
            tts_config=self._prepare_tts_config(agent_config),
            llm_config=self._prepare_llm_config(agent_config),
            instructions=agent_config.get(
                "assistant_instruction", "You are a helpful voice AI assistant."),
            welcome_message=agent_config.get(
                "static_message", "Hello! How can I help you today?"),
            welcome_type=agent_config.get(
                "welcome_message_type", "user_initiates")
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
        return {
            "end_call_on_silence": config.get("end_call_on_silence", False),
            "silence_duration": config.get("silence_duration", 60),
            "max_call_duration": config.get("max_call_duration", 1800),
            "tools": config.get("tools", {
                "email": False,
                "calendar": False,
                "knowledge_base": False
            })
        }

    async def start_session(self) -> None:
        """Start the agent session"""
        await self._load_config()

        # Create model components
        stt = ModelFactory.create_stt(self._config.stt_config)
        llm = ModelFactory.create_llm(self._config.llm_config)
        tts = ModelFactory.create_tts(self._config.tts_config)

        self._session = AgentSession(
            stt=stt,
            llm=llm,
            tts=tts,
            vad=silero.VAD.load(min_silence_duration=0.20),
            turn_detection=MultilingualModel(),
        )

        # Start session
        await self._session.start(
            room=self._room_name,
            agent=self,
            room_input_options=RoomInputOptions(
                noise_cancellation=self._noise_cancellation,
            ),
        )

        # Generate welcome message
        await self._session.generate_reply(
            instructions=f"Greet the user with: {self._config.welcome_message}"
        )

    async def end_session(self, reason: str = None) -> None:
        """End the agent session"""
        if self._session:
            await self._session.stop()

        if reason:
            await end_call_recording(
                call_id=self._call_id,
                status="dropped",
                reason=reason
            )
        else:
            await end_call_recording(
                call_id=self._call_id,
                status="completed",
                outcomes={
                    "final_stage": self._current_stage,
                    "successful": True
                }
            )


async def entrypoint(ctx: agents.JobContext):
    """Entry point for the agent service"""
    assistant = None
    try:
        # Create and initialize the assistant
        assistant = Assistant()
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
        if assistant and assistant.call_id:
            await assistant.end_session(str(e))
        raise


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
