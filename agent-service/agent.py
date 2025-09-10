import asyncio
from dotenv import load_dotenv
import re
import json
from typing import Dict, Any, Optional, Tuple

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.rtc import Room

# Default plugins
from livekit.plugins import silero, openai, cartesia, deepgram
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# All plugin instantiation is handled by the factory
from config.config_definitions import DEFAULT_SETTINGS
from utils.plugin_factory import create_stt_plugin, create_llm_plugin, create_tts_plugin
from utils.context_manager import get_context_for_user, cleanup_context
from utils.database import get_agent_config_from_db_by_phone
from utils.business_tools import (
    query_user_information, book_user_appointment,
    check_user_availability, update_user_crm
)

load_dotenv()


class Assistant(Agent):
    def __init__(self, instructions=None) -> None:
        if not instructions:
            instructions = "You are a helpful assistant. You can answer questions, provide information, and assist users with various tasks. Always be polite and helpful."
        super().__init__(instructions=instructions)

        # Context will be initialized later when we have user_id
        self.user_id = None
        self.conversation_context = None
        self._keep_alive_task = None

    async def initialize_context(self, user_id: str, initial_context: dict = None):
        """Initialize conversation context with user ID and initial context from database"""
        self.user_id = user_id
        if user_id and user_id != "default_user":
            try:
                self.conversation_context = await get_context_for_user(user_id, initial_context)
                print(f"Initialized conversation context for user: {user_id}")
            except Exception as e:
                print(f"Error initializing context for {user_id}: {e}")
                self.conversation_context = None

    async def keep_alive(self, room: Room):
        """Task to keep agent connection alive by sending metadata updates"""
        try:
            # Skip heartbeat functionality since it's causing errors and not needed
            while True:
                # Just keep the task running without doing anything
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            # Expected on cleanup
            print("Keep-alive task cancelled")
        except Exception as e:
            print(f"Keep-alive task failed: {e}")

    def start_keep_alive(self, room: Room):
        """Start background task to keep connection alive"""
        if not self._keep_alive_task or self._keep_alive_task.done():
            try:
                self._keep_alive_task = asyncio.create_task(
                    self.keep_alive(room))
                print("Started keep-alive background task")
                return True
            except Exception as e:
                print(f"Error starting keep-alive task: {e}")
                return False
        else:
            print("Keep-alive task already running")
            return True

    def stop_keep_alive(self):
        """Stop the keep-alive task if it's running"""
        if self._keep_alive_task and not self._keep_alive_task.done():
            try:
                self._keep_alive_task.cancel()
                print("Cancelled keep-alive task")
            except Exception as e:
                print(f"Error cancelling keep-alive task: {e}")

    async def get_context_summary(self):
        """Get current conversation context"""
        if self.conversation_context:
            return await self.conversation_context.get_current_context()
        return {"error": "No context available"}

    async def update_client_info(self, field: str, value: str):
        """Update client information"""
        if self.conversation_context:
            return await self.conversation_context.update_business_info(field, value)
        return False

    async def advance_conversation_stage(self, stage: str):
        """Advance to next conversation stage"""
        if self.conversation_context:
            return await self.conversation_context.advance_stage(stage)
        return stage

    async def get_next_suggestion(self):
        """Get suggestion for next action"""
        if self.conversation_context:
            return await self.conversation_context.get_next_action_suggestion()
        return "Continue the conversation"

    async def query_knowledge_base(self, query: str):
        """Query vector database for information"""
        if self.user_id:
            try:
                response = await query_user_information(self.user_id, query)
                print(f"Knowledge query result: {response[:100]}...")
                return response
            except Exception as e:
                print(f"Error querying knowledge base: {e}")
                return "I'm sorry, I couldn't find that information right now."
        return "I need to establish context first before I can help with specific questions."

    async def book_appointment(self, appointment_details: Dict[str, Any]):
        """Book an appointment for the user"""
        if self.user_id:
            try:
                result = await book_user_appointment(self.user_id, appointment_details)
                print(f"Appointment booking result: {result}")
                return result
            except Exception as e:
                print(f"Error booking appointment: {e}")
                return {
                    "success": False,
                    "message": "Unable to book appointment at this time"
                }
        return {"success": False, "message": "User context not available"}

    async def check_availability(self, date: str, service_type: str = None):
        """Check appointment availability"""
        if self.user_id:
            try:
                result = await check_user_availability(self.user_id, date, service_type)
                print(f"Availability check result: {result}")
                return result
            except Exception as e:
                print(f"Error checking availability: {e}")
                return {
                    "success": False,
                    "message": "Unable to check availability right now"
                }
        return {"success": False, "message": "User context not available"}

    async def update_customer_record(self, additional_info: Dict[str, Any] = None):
        """Update customer record in CRM"""
        if self.user_id:
            try:
                result = await update_user_crm(self.user_id, additional_info)
                print(f"CRM update result: {result}")
                return result
            except Exception as e:
                print(f"Error updating CRM: {e}")
                return {
                    "success": False,
                    "message": "Unable to update customer record right now"
                }
        return {"success": False, "message": "User context not available"}


def _parse_json_metadata(meta: Optional[str]) -> Dict[str, Any]:
    """Safely parse JSON-encoded metadata strings into dicts."""
    if not meta or not isinstance(meta, str):
        return {}
    try:
        return json.loads(meta)
    except Exception:
        return {}


def extract_numbers_from_context(ctx: agents.JobContext) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract agent (called/DID) phone number and caller phone number from richer context
    like room metadata, participant metadata, or job metadata.

    Returns: (agent_phone, caller_phone, call_type)
    call_type can be "inbound" or "outbound" if available in metadata; otherwise None.
    """
    agent_phone: Optional[str] = None
    caller_phone: Optional[str] = None
    call_type: Optional[str] = None

    # 1) Room metadata (recommended to set via your backend when creating the room)
    if hasattr(ctx, 'room') and ctx.room:
        room_meta = _parse_json_metadata(getattr(ctx.room, 'metadata', None))
        # Common keys to check for agent/called DID
        for key in ['agent_phone', 'to_number', 'called_number', 'did', 'destination', 'sip_to', 'sipTo']:
            if not agent_phone and isinstance(room_meta.get(key), str):
                agent_phone = room_meta.get(key)
        for key in ['caller_phone', 'from_number', 'caller', 'sip_from', 'sipFrom']:
            if not caller_phone and isinstance(room_meta.get(key), str):
                caller_phone = room_meta.get(key)
        if isinstance(room_meta.get('direction'), str):
            call_type = room_meta.get('direction')

    # 2) Participant metadata (SIP gateways often include SIP headers here)
    try:
        if hasattr(ctx, 'room') and ctx.room and hasattr(ctx.room, 'participants'):
            for participant in ctx.room.participants:
                # Handle case where metadata is a string value directly
                raw_metadata = getattr(participant, 'metadata', None)
                if isinstance(raw_metadata, str) and raw_metadata.strip().lower() == "outbound":
                    call_type = "outbound"
                    print(
                        f"Detected outbound call from direct participant metadata: {raw_metadata}")
                    continue

                # Continue with JSON parsing for structured metadata
                pmeta = _parse_json_metadata(raw_metadata)
                for key in ['to_number', 'called_number', 'did', 'destination', 'sip_to', 'sipTo', 'agent_phone']:
                    if not agent_phone and isinstance(pmeta.get(key), str):
                        agent_phone = pmeta.get(key)
                for key in ['from_number', 'caller', 'caller_phone', 'sip_from', 'sipFrom']:
                    if not caller_phone and isinstance(pmeta.get(key), str):
                        caller_phone = pmeta.get(key)
                if isinstance(pmeta.get('direction'), str) and not call_type:
                    call_type = pmeta.get('direction')
    except Exception as e:
        print(f"Error processing participant metadata: {e}")
        pass

    # 3) Job metadata (if your infra passes details when scheduling the agent)
    try:
        job_meta = _parse_json_metadata(
            getattr(getattr(ctx, 'job', None), 'metadata', None))
        for key in ['agent_phone', 'to_number', 'called_number', 'did', 'destination']:
            if not agent_phone and isinstance(job_meta.get(key), str):
                agent_phone = job_meta.get(key)
        for key in ['caller_phone', 'from_number', 'caller']:
            if not caller_phone and isinstance(job_meta.get(key), str):
                caller_phone = job_meta.get(key)
        if isinstance(job_meta.get('direction'), str) and not call_type:
            call_type = job_meta.get('direction')
    except Exception:
        pass

    return agent_phone, caller_phone, call_type


async def entrypoint(ctx: agents.JobContext):
    user_id: Optional[str] = None
    try:
        phone_number = None
        call_type = "inbound"

        # Connect early to satisfy LiveKit worker timing (avoid 10s warning)
        try:
            await ctx.connect()
            print("Connected to LiveKit room successfully")
        except Exception as e:
            print(
                f"Warning: initial ctx.connect() failed, will retry later: {e}")

        # Extract phone number early for logging
        if hasattr(ctx, 'room') and ctx.room and isinstance(ctx.room.name, str):
            print(f"Room name: {ctx.room.name}")
            # Extract first E.164-like number anywhere in the room name (e.g., twilio-+E164-...)
            match = re.search(r"\+\d{6,15}", ctx.room.name)
            if match:
                phone_number = match.group(0)
                print(
                    f"Identified phone number from room name: {phone_number}")

        # Now proceed with the rest of initialization in parallel
        # Prefer extracting from call context (metadata) over parsing room name
        agent_phone, caller_phone, inferred_call_type = extract_numbers_from_context(
            ctx)
        if agent_phone:
            phone_number = agent_phone
            print(f"Identified agent phone from context: {phone_number}")
        if inferred_call_type:
            # Normalize common variants
            lc = inferred_call_type.strip().lower()
            if lc in {"in", "incoming", "inbound"}:
                call_type = "inbound"
            elif lc in {"out", "outgoing", "outbound"}:
                call_type = "outbound"

        # Fallback to room name pattern only if not found in metadata
        if not phone_number and hasattr(ctx, 'room') and ctx.room and isinstance(ctx.room.name, str):
            print(f"Room name: {ctx.room.name}")
            # Extract first E.164-like number anywhere in the room name (e.g., twilio-+E164-...)
            match = re.search(r"\+\d{6,15}", ctx.room.name)
            if match:
                phone_number = match.group(0)
                print(
                    f"Identified phone number from room name: {phone_number}")

        agent_config = DEFAULT_SETTINGS.copy()

        if phone_number:
            db_config = await get_agent_config_from_db_by_phone(phone_number, call_type)
            if not db_config:
                print(
                    f"No specific config for {phone_number} ({call_type}), trying default.")
                db_config = await get_agent_config_from_db_by_phone("default", call_type)
        else:
            print("Could not identify phone number, using default config.")
            db_config = await get_agent_config_from_db_by_phone("default", call_type)

        if db_config:
            print("Loaded configuration from DB.")
            agent_config.update(db_config)
        else:
            print(
                "No dynamic or default configuration found in DB, using static settings.")

        # The user_id is useful for session-specific context
        # Handle Room.sid being a coroutine in some SDK versions
        sid_value = getattr(ctx.room, 'sid', None)
        sid_str: Optional[str] = None
        try:
            if asyncio.iscoroutine(sid_value):
                sid_str = await sid_value
            elif callable(sid_value):
                maybe = sid_value()
                sid_str = await maybe if asyncio.iscoroutine(maybe) else str(maybe)
            elif sid_value is not None:
                sid_str = str(sid_value)
        except Exception:
            sid_str = None
        if not sid_str:
            sid_str = getattr(ctx.room, 'name', 'unknown') or 'unknown'
        user_id = f"session_{sid_str}"

        # Create plugins based on the loaded agent_config
        try:
            stt_plugin = create_stt_plugin(agent_config)
            llm_plugin = create_llm_plugin(agent_config)
            tts_plugin = create_tts_plugin(agent_config)
        except Exception as e:
            print(f"Error creating custom plugins from settings: {e}")
            print("Falling back to default plugin configuration")
            # Fall back to default plugins if there's an issue with settings
            stt_plugin = deepgram.STT(model="nova-2-general", language="fr")
            llm_plugin = openai.LLM(model="gpt-4o-mini")
            tts_plugin = cartesia.TTS(
                language='fr', voice="5c3c89e5-535f-43ef-b14d-f8ffe148c1f0")

        # Create the agent session with plugins
        session = AgentSession(
            stt=stt_plugin,
            llm=llm_plugin,
            tts=tts_plugin,
            vad=silero.VAD.load(min_silence_duration=0.10),
            turn_detection=MultilingualModel(),
        )

        # Get custom instructions if available
        instructions = agent_config.get(
            "assistant_instructions",
            "You are a helpful assistant. You can answer questions, provide information, and assist users with various tasks. Always be polite and helpful.",
        )

        # Create assistant with instructions (no user_id in constructor)
        assistant = Assistant(instructions=instructions)

        # Extract initial context from database configuration
        initial_context = agent_config.get("initial_context", {})

        # Initialize conversation context after creation with initial context from DB
        await assistant.initialize_context(user_id, initial_context)

        # Start keep-alive task to maintain connection
        assistant.start_keep_alive(ctx.room)

        print("Starting fully configured agent session...")

        # Configure room options for the main session for better reliability
        main_room_options = RoomInputOptions()
        main_room_options.reduce_latency = True
        main_room_options.optimize_for_voice = True
        # Longer timeout (60s)
        main_room_options.audio_stream_timeout_ms = 60000

        try:
            await session.start(
                room=ctx.room,
                agent=assistant,
                room_input_options=main_room_options,
            )
            print("Agent session started; sending welcome message...")
        except Exception as e:
            print(f"Error starting agent session: {e}")
            # Try connecting directly if session start failed
            try:
                print("Attempting direct room connection...")
                if not ctx.room.connected:
                    await ctx.connect()
                print("Direct connection successful")
            except Exception as inner_e:
                print(f"Direct connection also failed: {inner_e}")
                raise  # Re-raise the exception to exit gracefully

        # Get custom welcome message if available
        default_welcome = (
            "Bonjour, je suis Pascal de Pôle démarches. je vous appelle suite à votre demande liée à l'obtention d'un logement social de type HLM"
        )
        welcome_message = agent_config.get("welcome_message", default_welcome)

        # Speak proactively to avoid long initial silence on SIP calls
        await session.say(welcome_message)
        print("Welcome message sent.")
    except Exception as e:
        print(f"Error in agent entrypoint: {e}")
        # Stop any keep-alive tasks
        if 'assistant' in locals() and assistant:
            assistant.stop_keep_alive()
        # Cleanup context on error
        if user_id:
            try:
                await cleanup_context(user_id)
            except:  # noqa: E722
                pass
        raise  # Re-raise the exception so LiveKit can handle it


if __name__ == "__main__":
    # Let LiveKit CLI manage the event loop
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))