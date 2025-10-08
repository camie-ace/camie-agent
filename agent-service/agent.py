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
from utils.room_extractor import extract_room_name, extract_phone_number
from utils.call_history import (
    start_call_recording,
    update_call_config,
    update_call_stage,
    end_call_recording
)

# Configure logging
logger = logging.getLogger(__name__)

load_dotenv()


class Assistant(Agent):
    def __init__(self, instructions: str = "You are a helpful voice AI assistant.", call_id: str = None) -> None:
        super().__init__(instructions=instructions)
        self.call_id = call_id
        self.current_stage = "greeting"

    async def on_stage_update(self, stage: str) -> None:
        """Handle stage updates and record them in call history"""
        self.current_stage = stage
        if self.call_id:
            await update_call_stage(self.call_id, stage)
            logger.info(f"Call {self.call_id}: Stage updated to {stage}")


async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()

    @ctx.room.on("participant_connected")
    def on_participant_connected(participant: rtc.RemoteParticipant):
        if participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP:
            # Extract basic participant info
            phone_number = participant.identity
            logger.info(f"Participant connected: {participant}")
            logger.info(f"Participant identity (phone number): {phone_number}")

            # Log all SIP-related attributes
            sip_details = {
                'identity': phone_number,
                'name': participant.name,
                'metadata': participant.metadata
            }

            # Extract all SIP-specific attributes
            sip_attributes = {
                key: value for key, value in participant.attributes.items()
                if key.startswith('sip_')
            }
            sip_details.update(sip_attributes)

            # Log comprehensive SIP details
            logger.info("SIP Call Details:")
            for key, value in sip_details.items():
                logger.info(f"  {key}: {value}")

            # Extract commonly used SIP fields
            caller_number = participant.attributes.get('sip_from', 'unknown')
            dialed_number = participant.attributes.get('sip_to', 'unknown')
            call_id = participant.attributes.get('sip_call_id', 'unknown')
            request_uri = participant.attributes.get(
                'sip_request_uri', 'unknown')

            logger.info(f"Caller Number: {caller_number}")
            logger.info(f"Dialed Number: {dialed_number}")
            logger.info(f"Call ID: {call_id}")
            logger.info(f"Request URI: {request_uri}")

    # Extract room name using our utility function
    room_name = extract_room_name(ctx)
    logger.info(f"Processing job request for room: {room_name}")
    logger.info(f"Full job context: {JobProcess}")

    # Extract phone number from room name
    phone_number = extract_phone_number(room_name)
    if phone_number:
        logger.info(f"Extracted phone number: {phone_number}")
    else:
        logger.warning(
            f"Could not extract phone number from room name: {room_name}")
        phone_number = "unknown"

    # Start call recording
    call_id = await start_call_recording(
        phone_number=phone_number,
        room_name=room_name,
        call_type="inbound"  # Default to inbound, could be determined from context
    )
    logger.info(f"Started call recording with ID: {call_id}")

    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()

    def handle_signal(sig, frame):
        logger.info(f"Received signal {sig}, ending call recording")
        asyncio.create_task(end_call_with_reason(call_id, "system_interrupt"))

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: handle_signal(s, None))

    # Get participant metadata if available
    participant_metadata = None
    logger.info(f"Job Context: {ctx}")
    logger.info(f"Job: {ctx.job}")
    logger.info(f"Room: {ctx.room}")
    if ctx.room:
        logger.info(f"Local participant: {ctx.room.local_participant}")
        if ctx.room.local_participant:
            logger.info(
                f"Metadata type: {type(ctx.room.local_participant.metadata)}")
            logger.info(
                f"Metadata value: {ctx.room.local_participant.metadata}")
    if ctx.room and ctx.room.local_participant and ctx.room.local_participant.metadata:
        try:
            metadata_str = ctx.room.local_participant.metadata
            participant_metadata = json.loads(metadata_str)
            logger.info(f"Participant metadata: {participant_metadata}")
        except json.JSONDecodeError:
            logger.error(
                f"Failed to parse participant metadata: {ctx.room.local_participant.metadata}")

    try:
        # Fetch agent configuration using room name and metadata
        agent_config = await get_agent_config_from_room(room_name, participant_metadata)

        # Update call record with agent configuration
        await update_call_config(call_id, agent_config)

        # Log the configuration
        logger.info(
            f"Using agent configuration: {json.dumps(agent_config, indent=2)}")

        # Extract config sections
        stt_config = agent_config.get("stt", {})
        llm_config = agent_config.get("llm", {})
        tts_config = agent_config.get("tts", {})
        assistant_instructions = agent_config.get(
            "assistant_instructions", "You are a helpful voice AI assistant.")
        welcome_message = agent_config.get(
            "welcome_message", "Hello! How can I assist you today?")

        # Dynamically create model components based on configuration
        stt = ModelFactory.create_stt(stt_config)
        llm = ModelFactory.create_llm(llm_config)
        tts = ModelFactory.create_tts(tts_config)

        # Create Assistant with call ID for tracking
        assistant = Assistant(
            instructions=assistant_instructions, call_id=call_id)

        session = AgentSession(
            stt=stt,
            llm=llm,
            tts=tts,
            vad=silero.VAD.load(min_silence_duration=0.20),
            turn_detection=MultilingualModel(),
        )

        await session.start(
            room=ctx.room,
            agent=assistant,
            room_input_options=RoomInputOptions(
                noise_cancellation=noise_cancellation.BVCTelephony(),
            ),
        )

        # Generate welcome message
        await session.generate_reply(
            instructions=f"Greet the user with: {welcome_message}"
        )

        # Record successful call completion
        await end_call_recording(
            call_id=call_id,
            status="completed",
            outcomes={
                "final_stage": assistant.current_stage,
                "successful": True
            }
        )

    except Exception as e:
        logger.error(f"Error in agent entrypoint: {e}")
        # Record failed call
        await end_call_recording(
            call_id=call_id,
            status="failed",
            reason=str(e),
            outcomes={
                "successful": False,
                "notes": f"Error: {str(e)}"
            }
        )
        raise


async def end_call_with_reason(call_id: str, reason: str):
    """Helper function to end a call with a specific reason"""
    await end_call_recording(
        call_id=call_id,
        status="dropped",
        reason=reason
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
