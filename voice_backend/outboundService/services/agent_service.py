import os
import json
import asyncio
import logging
import sys
from datetime import datetime
from livekit import api
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, function_tool, RunContext, get_job_context
from livekit.plugins import (
    openai,
    cartesia,
    deepgram,
    noise_cancellation,
    silero,
    google
)
from dotenv import load_dotenv
from common.config.settings import (
    TTS_MODEL, TTS_VOICE, STT_MODEL, STT_LANGUAGE, LLM_MODEL, TRANSCRIPT_DIR, PARTICIPANT_IDENTITY
)
from common.update_config import load_dynamic_config

load_dotenv()

# ------------------------------------------------------------
# Environment / LiveKit admin credentials (fetched from env)
# ------------------------------------------------------------
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

# ------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("agent_debug.log")
    ]
)
logger = logging.getLogger("services.agent_service")

logger.info("=" * 60)
logger.info("Agent Service Module Loading")
logger.info(f"LIVEKIT_URL: {LIVEKIT_URL or 'NOT SET'}")
logger.info(f"LIVEKIT_API_KEY: {'SET' if LIVEKIT_API_KEY else 'NOT SET'}")
logger.info(f"LIVEKIT_API_SECRET: {'SET' if LIVEKIT_API_SECRET else 'NOT SET'}")
logger.info(f"OPENAI_API_KEY: {'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET'}")
logger.info(f"STT_MODEL: {STT_MODEL}")
logger.info(f"LLM_MODEL: {LLM_MODEL}")
logger.info("=" * 60)


# ------------------------------------------------------------
# Utility: cleanup previous rooms with safe guards
# ------------------------------------------------------------
async def cleanup_previous_rooms(api_key, api_secret, server_url, prefix="agent-room"):
    """
    Attempt to delete previously created rooms whose name starts with `prefix`.
    This function is defensive: if the admin API isn't available it logs and continues.
    """
    if not (api_key and api_secret and server_url):
        logger.warning("LiveKit admin credentials or URL not provided — skipping room cleanup.")
        return

    try:
        logger.info("Attempting to list & cleanup previous rooms (prefix=%s)...", prefix)
        # RoomService behavior may vary by SDK version. We try the typical async interface.
        room_service = api.RoomService(api_key=api_key, api_secret=api_secret, host=server_url)
        active_rooms = await room_service.list_rooms()
        # active_rooms may be an object with .rooms or be a list depending on SDK
        rooms_iterable = getattr(active_rooms, "rooms", active_rooms)
        deleted = 0
        for room in rooms_iterable:
            name = getattr(room, "name", None) or room
            if name and name.startswith(prefix):
                logger.info("🧹 Deleting old room: %s", name)
                try:
                    # Try typical call patterns for different SDK versions:
                    if hasattr(room_service, "delete_room"):
                        # Some SDKs accept a string, some require a request object
                        try:
                            await room_service.delete_room(name)
                        except TypeError:
                            # fallback to api.DeleteRoomRequest
                            await room_service.delete_room(api.DeleteRoomRequest(room=name))
                    else:
                        # as a last resort, use the low-level admin API if available
                        await api.RoomService(api_key=api_key, api_secret=api_secret, host=server_url).delete_room(name)
                    deleted += 1
                except Exception as e:
                    logger.warning("Failed to delete room %s: %s", name, e)
        logger.info("🧹 Room cleanup finished — deleted %d rooms matching prefix '%s'", deleted, prefix)
    except Exception as e:
        logger.warning("Room cleanup failed (non-fatal). Reason: %s", e, exc_info=True)


# ------------------------------------------------------------
# Assistant definition
# ------------------------------------------------------------
class Assistant(Agent):
    def __init__(self, instructions: str = None) -> None:
        if instructions is None:
            instructions = os.getenv("AGENT_INSTRUCTIONS", "You are a helpful voice AI assistant.")
        logger.info(f"Agent initialized with instructions: {instructions}")
        super().__init__(instructions=instructions)

    @function_tool
    async def transfer_to_human(self, ctx: RunContext) -> str:
        """Transfer active SIP caller to a human number."""
        job_ctx = get_job_context()
        if job_ctx is None:
            logger.error("Job context not found")
            return "error"

        transfer_to = "tel:+919911062767"

        sip_participant = None
        for participant in job_ctx.room.remote_participants.values():
            if participant.identity == "sip-caller":
                sip_participant = participant
                break

        if sip_participant is None:
            logger.error("No SIP participant found to transfer")
            return "error"

        try:
            await job_ctx.api.sip.transfer_sip_participant(
                api.TransferSIPParticipantRequest(
                    room_name=job_ctx.room.name,
                    participant_identity=sip_participant.identity,
                    transfer_to=transfer_to,
                    play_dialtone=True
                )
            )
            logger.info(f"Transferred participant {sip_participant.identity} to {transfer_to}")
            return "transferred"
        except Exception as e:
            logger.error(f"Failed to transfer call: {e}", exc_info=True)
            return "error"

    @function_tool
    async def end_call(self, ctx: RunContext) -> str:
        """End call gracefully."""
        logger_local = logging.getLogger("phone-assistant")
        job_ctx = get_job_context()
        if job_ctx is None:
            logger_local.error("Failed to get job context")
            return "error"

        try:
            await job_ctx.api.room.delete_room(api.DeleteRoomRequest(room=job_ctx.room.name))
            logger_local.info(f"Successfully ended call for room {job_ctx.room.name}")
            return "ended"
        except Exception as e:
            logger_local.error(f"Failed to end call: {e}", exc_info=True)
            return "error"


# ------------------------------------------------------------
# Agent entrypoint
# ------------------------------------------------------------
async def entrypoint(ctx: agents.JobContext):
    """Main entrypoint for the voice agent service."""
    logger.info("=" * 60)
    logger.info(f"ENTRYPOINT CALLED - Room: {ctx.room.name}")
    logger.info("=" * 60)

    # Load dynamic configuration from config.json
    try:
        logger.info("Loading dynamic configuration from config.json...")
        dynamic_config = load_dynamic_config()
        
        caller_name = dynamic_config.get("caller_name", "Guest")
        dynamic_instruction = dynamic_config.get("agent_instructions", "You are a helpful voice AI assistant.")
        language = dynamic_config.get("tts_language", "en")
        emotion = dynamic_config.get("tts_emotion", "Calm")
        
        logger.info("✓ Dynamic configuration loaded successfully")
        logger.info(f"  - Caller Name: {caller_name}")
        logger.info(f"  - TTS Language: {language}")
        logger.info(f"  - TTS Emotion: {emotion}")
        logger.info(f"  - Agent Instructions: {dynamic_instruction[:100]}...")
    except Exception as e:
        logger.warning(f"Failed to load dynamic config, using defaults: {str(e)}")
        caller_name = "Guest"
        dynamic_instruction = "You are a helpful voice AI assistant."
        language = "en"
        emotion = "Calm"
    
    # Static config from environment
    room_prefix_for_cleanup = os.getenv("ROOM_CLEANUP_PREFIX", "agent-room")

    # --------------------------------------------------------
    # Prepare cleanup callback (save transcript)
    # --------------------------------------------------------
    async def cleanup_and_save():
        try:
            logger.info("Cleanup started...")
            os.makedirs(TRANSCRIPT_DIR, exist_ok=True)
            filename = f"{TRANSCRIPT_DIR}/transcript.json"

            # session may not be defined if start() failed — guard it
            if "session" in locals() and session is not None and hasattr(session, "history"):
                with open(filename, "w") as f:
                    json.dump(session.history.to_dict(), f, indent=2)
                logger.info(f"Transcript saved to {filename}")
            else:
                logger.warning("No session history to save (session not created or no history).")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)

    ctx.add_shutdown_callback(cleanup_and_save)
    logger.info("[OK] Shutdown callback added")

    # --------------------------------------------------------
    # Initialize core components
    # --------------------------------------------------------
    try:
        logger.info("Initializing session components...")

        logger.info("Step 1: Initializing STT (Deepgram)")
        stt_instance = deepgram.STT(model=STT_MODEL, language=STT_LANGUAGE)

        logger.info("Step 2: Initializing LLM (OpenAI)")
        llm_instance = openai.LLM(model=LLM_MODEL)

        logger.info("Step 3: Initializing TTS (Cartesia)")
        tts_instance = cartesia.TTS(model=TTS_MODEL, emotion=emotion, language=language)

        logger.info("Step 4: Creating AgentSession")
        session = AgentSession(stt=stt_instance, llm=llm_instance, tts=tts_instance)
        logger.info("[OK] All session components initialized")
    except Exception as e:
        logger.error(f"[ERROR] Failed initializing session components: {e}", exc_info=True)
        raise

    # --------------------------------------------------------
    # Optional: cleanup previous rooms BEFORE connecting
    # --------------------------------------------------------
    try:
        await cleanup_previous_rooms(LIVEKIT_API_KEY, LIVEKIT_API_SECRET, LIVEKIT_URL, prefix=room_prefix_for_cleanup)
    except Exception as e:
        logger.warning("cleanup_previous_rooms raised an exception (non-fatal): %s", e, exc_info=True)

    # --------------------------------------------------------
    # Connect to room
    # --------------------------------------------------------
    try:
        logger.info("Connecting to room...")
        await ctx.connect()
        logger.info("[OK] Connected to room successfully")
    except Exception as e:
        logger.error("Failed to connect to room: %s", e, exc_info=True)
        # If connection fails, raise so the worker can restart or exit cleanly
        raise

    # --------------------------------------------------------
    # Initialize assistant and start session
    # --------------------------------------------------------
    assistant = Assistant(instructions=dynamic_instruction)
    room_options = RoomInputOptions(noise_cancellation=noise_cancellation.BVC())

    try:
        logger.info("Starting agent session...")
        await session.start(room=ctx.room, agent=assistant, room_input_options=room_options)
        logger.info("[OK] Agent session started successfully")
    except Exception as e:
        logger.error("Failed to start AgentSession: %s", e, exc_info=True)
        # ensure we attempt a graceful shutdown/cleanup
        try:
            await ctx.shutdown()
        except Exception:
            pass
        raise

    # --------------------------------------------------------
    # Greeting logic AFTER session start and stream stabilization
    # --------------------------------------------------------
    await asyncio.sleep(2)  # Let audio streams stabilize

    greeting_instruction = (
        f"Hello {caller_name}, I’m your cricket coach from Island AI. "
        "How are you today? What would you like to practice?"
    )
    try:
        # Guard that session is running (some SDKs expose is_running)
        is_running = getattr(session, "is_running", None)
        if is_running is None or is_running:
            await session.generate_reply(instructions=greeting_instruction)
            logger.info("[OK] Greeting sent successfully")
        else:
            logger.warning("Session reports not running — skipping greeting.")
    except Exception as e:
        logger.error(f"[ERROR] Failed sending greeting: {e}", exc_info=True)

    # --------------------------------------------------------
    # Wait for shutdown (updated API)
    # --------------------------------------------------------
    logger.info("Session running — waiting for termination signal...")
    try:
        # newer livekit.agents versions use wait_for_termination()
        if hasattr(ctx, "wait_for_termination"):
            await ctx.wait_for_termination()
        else:
            # fallback to run_forever
            await agents.run_forever()
    except Exception as e:
        logger.error(f"[ERROR] Error while waiting for shutdown: {e}", exc_info=True)
    finally:
        logger.info("=" * 60)
        logger.info(f"ENTRYPOINT FINISHED - Room: {ctx.room.name}")
        logger.info("=" * 60)


# ------------------------------------------------------------
# CLI entrypoint
# ------------------------------------------------------------
def run_agent():
    """Run the agent CLI worker."""
    logger.info("=" * 60)
    logger.info("RUN_AGENT CALLED - Starting LiveKit Agent CLI")
    logger.info("=" * 60)
    try:
        agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
    except Exception as e:
        logger.error(f"[ERROR] Fatal error in run_agent: {e}", exc_info=True)
        raise
