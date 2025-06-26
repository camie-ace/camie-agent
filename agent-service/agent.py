import asyncio
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions

# Default plugins
from livekit.plugins import silero, openai, cartesia, deepgram
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# All plugin instantiation is handled by the factory
from config.config_definitions import DEFAULT_SETTINGS
from config.settings_manager import get_user_settings
from utils.plugin_factory import create_stt_plugin, create_llm_plugin, create_tts_plugin
from utils.redis_utils import close_redis_pool

load_dotenv()


class Assistant(Agent):
    def __init__(self, instructions=None) -> None:
        if not instructions:
            instructions = "You are a helpful assistant. You can answer questions, provide information, and assist users with various tasks. Always be polite and helpful."
        super().__init__(instructions=instructions)


async def entrypoint(ctx: agents.JobContext):
    try:

        user_id = ""
        if ctx.request and ctx.request.participant:
            user_id = ctx.request.participant.identity
            print(f"Using participant identity as user_id: {user_id}")
        elif ctx.room:
            user_id = f"room_{ctx.room.name}"
            print(f"Using room name as user identifier: {user_id}")

        # Get user settings if available, otherwise fall back to defaults
        if user_id:
            try:
                user_settings = await get_user_settings(user_id)
                print(f"Loaded settings for user: {user_id}")
            except Exception as e:
                print(f"Error loading user settings: {e}, using defaults")
                user_settings = DEFAULT_SETTINGS.copy()
        else:
            user_settings = DEFAULT_SETTINGS.copy()
            print("No user_id available, using default settings")

        # Create plugins based on user settings
        try:
            stt_plugin = create_stt_plugin(user_settings)
            llm_plugin = create_llm_plugin(user_settings)
            tts_plugin = create_tts_plugin(user_settings)
        except Exception as e:
            print(f"Error creating custom plugins from settings: {e}")
            print("Falling back to default plugin configuration")
            # Fall back to default plugins if there's an issue with settings
            stt_plugin = deepgram.STT(model="nova-2-phonecall", language="en")
            llm_plugin = openai.LLM(model="gpt-4o-mini")
            tts_plugin = cartesia.TTS(
                language='en', voice="c99d36f3-5ffd-4253-803a-535c1bc9c306")

        # Create the agent session with plugins
        session = AgentSession(
            stt=stt_plugin,
            llm=llm_plugin,
            tts=tts_plugin,
            vad=silero.VAD.load(min_silence_duration=0.10),
            turn_detection=MultilingualModel(),
        )

        # Get custom instructions if available
        instructions = user_settings.get("assistant_instructions",
                                         "You are a helpful assistant. You can answer questions, provide information, and assist users with various tasks. Always be polite and helpful.")
        await session.start(
            room=ctx.room,
            agent=Assistant(instructions=instructions),
            room_input_options=RoomInputOptions(),
        )

        await ctx.connect()

        # Get custom welcome message if available
        welcome_message = user_settings.get("welcome_message",
                                            "Welcome, I am your assistant. How can I help you today?")

        await session.generate_reply(
            instructions=welcome_message,
        )
    except Exception as e:
        print(f"Error in agent entrypoint: {e}")
        # Attempt to close Redis connection on error
        try:
            await close_redis_pool()
        except:
            pass
        raise  # Re-raise the exception so LiveKit can handle it


if __name__ == "__main__":
    # Register Redis cleanup for when the process exits
    import atexit

    def cleanup_redis():
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(close_redis_pool())
            loop.close()
            print("Redis connection closed.")
        except Exception as e:
            print(f"Error during Redis cleanup: {e}")

    atexit.register(cleanup_redis)

    # Let LiveKit CLI manage the event loop
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
