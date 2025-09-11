from dotenv import load_dotenv
import json
import os
import logging

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import (
    noise_cancellation,
    silero,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from utils.config_fetcher import get_agent_config_from_room
from utils.model_factory import ModelFactory

# Configure logging
logger = logging.getLogger(__name__)

load_dotenv()


class Assistant(Agent):
    def __init__(self, instructions: str = "You are a helpful voice AI assistant.") -> None:
        super().__init__(instructions=instructions)


async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()

    # Extract room name from job context
    room_name = ctx.room_name
    logger.info(f"Processing job request for room: {room_name}")

    # Get participant metadata if available
    participant_metadata = None
    if ctx.room and ctx.room.local_participant and ctx.room.local_participant.metadata:
        try:
            metadata_str = ctx.room.local_participant.metadata
            participant_metadata = json.loads(metadata_str)
            logger.info(f"Participant metadata: {participant_metadata}")
        except json.JSONDecodeError:
            logger.error(
                f"Failed to parse participant metadata: {ctx.room.local_participant.metadata}")

    # Fetch agent configuration using room name and metadata
    agent_config = await get_agent_config_from_room(room_name, participant_metadata)

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

    session = AgentSession(
        stt=stt,
        llm=llm,
        tts=tts,
        vad=silero.VAD.load(min_silence_duration=0.50),
        turn_detection=MultilingualModel(),
    )

    await session.start(
        room=ctx.room,
        agent=Assistant(instructions=assistant_instructions),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVCTelephony(),
        ),
    )

    await session.generate_reply(
        instructions=f"Greet the user with: {welcome_message}"
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
