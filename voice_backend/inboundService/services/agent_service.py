import os
import logging
import sys
from livekit import api
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, function_tool, RunContext, get_job_context
from livekit.plugins import openai, deepgram, noise_cancellation, silero,elevenlabs
from dotenv import load_dotenv

load_dotenv()

# ------------------------------------------------------------
# Environment variables
# ------------------------------------------------------------
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

# Agent configuration
AGENT_INSTRUCTIONS = os.getenv("AGENT_INSTRUCTIONS", "You are a helpful voice AI assistant of Aistein.")
TRANSFER_NUMBER = os.getenv("TRANSFER_NUMBER", "+919911062767")

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
logger.info("Inbound Agent Service Starting")
logger.info(f"LIVEKIT_URL: {LIVEKIT_URL or 'NOT SET'}")
logger.info("=" * 60)


# ------------------------------------------------------------
# Simple Assistant class
# ------------------------------------------------------------
class Assistant(Agent):
    def __init__(self, instructions: str = None) -> None:
        if instructions is None:
            instructions = AGENT_INSTRUCTIONS or "You are a helpful voice AI assistant of Aistein."
        logger.info(f"Agent initialized with instructions: {instructions[:100]}...")
        super().__init__(instructions=instructions)

    @function_tool
    async def transfer_to_human(self, ctx: RunContext) -> str:
        """Transfer active SIP caller to a human number."""
        job_ctx = get_job_context()
        if job_ctx is None:
            logger.error("Job context not found")
            return "error"
        
        # Format transfer number
        transfer_to = TRANSFER_NUMBER if TRANSFER_NUMBER.startswith("tel:") else f"tel:{TRANSFER_NUMBER}"
        logger.info(f"Transfer requested to: {transfer_to}")

        # Find SIP participant
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
            logger.info(f"Transferred participant to {transfer_to}")
            return "transferred"
        except Exception as e:
            logger.error(f"Failed to transfer call: {e}", exc_info=True)
            return "error"

    @function_tool
    async def end_call(self, ctx: RunContext) -> str:
        """End call gracefully."""
        job_ctx = get_job_context()
        if job_ctx is None:
            logger.error("Failed to get job context")
            return "error"

        try:
            await job_ctx.api.room.delete_room(api.DeleteRoomRequest(room=job_ctx.room.name))
            logger.info(f"Successfully ended call for room {job_ctx.room.name}")
            return "ended"
        except Exception as e:
            logger.error(f"Failed to end call: {e}", exc_info=True)
            return "error"


# ------------------------------------------------------------
# Simple Agent entrypoint
# ------------------------------------------------------------
async def entrypoint(ctx: agents.JobContext):
    """Simple entrypoint for inbound voice agent."""
    logger.info("=" * 60)
    logger.info(f"Inbound Call - Room: {ctx.room.name}")
    logger.info("=" * 60)

    # Connect to room
    try:
        logger.info("Connecting to room...")
        await ctx.connect()
        logger.info("Connected to room")
    except Exception as e:
        logger.error(f"Failed to connect: {e}", exc_info=True)
        raise

    # Initialize components
    try:
        logger.info("Initializing STT, LLM, and TTS...")
        
        stt_instance = deepgram.STT(model="nova-2-general", language="en")
        llm_instance = openai.LLM(model="gpt-4o-mini")
        tts_instance = elevenlabs.TTS(
                voice_id="21m00Tcm4TlvDq8ikWAM",
                language="en",
                model="eleven_flash_v2_5"
            )
        
        logger.info("Creating session...")
        session = AgentSession(
            vad=silero.VAD.load(),
            stt=stt_instance,
            llm=llm_instance,
            tts=tts_instance
        )
        logger.info("Session components initialized")
    except Exception as e:
        logger.error(f"Failed to initialize: {e}", exc_info=True)
        raise

    # Create assistant and start session
    assistant = Assistant()
    room_options = RoomInputOptions(noise_cancellation=noise_cancellation.BVC())

    try:
        logger.info("Starting agent session...")
        await session.start(room=ctx.room, agent=assistant, room_input_options=room_options)
        logger.info("Agent session started")
    except Exception as e:
        logger.error(f"Failed to start session: {e}", exc_info=True)
        raise

    # Send greeting
    try:
        await session.generate_reply(instructions="Hello, I'm your AI assistant. How can I help you today?")
        logger.info("Greeting sent")
    except Exception as e:
        logger.error(f"Failed to send greeting: {e}", exc_info=True)

    # Wait for session to end
    logger.info("Session running...")
    logger.info("=" * 60)


# ------------------------------------------------------------
# CLI entrypoint
# ------------------------------------------------------------
def run_agent():
    """Run the inbound agent worker."""
    logger.info("=" * 60)
    logger.info("Starting Inbound Agent")
    logger.info("=" * 60)
    
    try:
        agent_name = "love-papa"
        logger.info(f"Agent name: {agent_name}")
        
        worker_options = agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name=agent_name,
        )
        
        agents.cli.run_app(worker_options)
        logger.info("Agent exited")
    except KeyboardInterrupt:
        logger.info("Agent stopped")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
