import os
import json
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from livekit import api, agents
from livekit.agents import (
    AgentSession, 
    Agent, 
    RoomInputOptions, 
    function_tool, 
    RunContext, 
    get_job_context
)
from livekit.plugins import openai, deepgram, elevenlabs, noise_cancellation

load_dotenv()

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

# Agent Configuration
AGENT_NAME = os.getenv("AGENT_NAME", "outbound-assistant")
AGENT_INSTRUCTIONS = os.getenv(
    "AGENT_INSTRUCTIONS",
    "You are a friendly outbound sales assistant. Be professional, concise, and helpful."
)

# Speech Configuration
STT_MODEL = "nova-2"
STT_LANGUAGE = "en-US"
LLM_MODEL = "gpt-4o"
TTS_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # ElevenLabs Rachel voice
TTS_LANGUAGE = "en"

# Transfer number (if needed)
TRANSFER_NUMBER = os.getenv("TRANSFER_NUMBER", "+1234567890")

# Transcript directory
TRANSCRIPT_DIR = Path("transcripts")
TRANSCRIPT_DIR.mkdir(exist_ok=True)

# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("agent.log")
    ]
)
logger = logging.getLogger("outbound_agent")

logger.info("=" * 60)
logger.info("Outbound Agent Initializing")
logger.info(f"LiveKit URL: {LIVEKIT_URL or 'NOT SET'}")
logger.info(f"Agent Name: {AGENT_NAME}")
logger.info(f"LLM Model: {LLM_MODEL}")
logger.info("Agent will auto-join ALL new rooms")
logger.info("=" * 60)


# ------------------------------------------------------------
# Assistant Definition
# ------------------------------------------------------------
class OutboundAssistant(Agent):
    """Simple outbound voice assistant with basic call management tools."""
    
    def __init__(self, instructions: str = AGENT_INSTRUCTIONS) -> None:
        super().__init__(instructions=instructions)
        logger.info(f"Assistant initialized with instructions: {instructions[:100]}...")

    @function_tool
    async def transfer_call(self, ctx: RunContext, reason: str = "") -> str:
        """
        Transfer the call to a human agent.
        
        Args:
            reason: Optional reason for transfer
            
        Returns:
            Status of the transfer operation
        """
        logger.info(f"Transfer requested. Reason: {reason}")
        
        job_ctx = get_job_context()
        if not job_ctx:
            logger.error("Job context not found")
            return "error: no job context"

        # Find SIP participant
        sip_participant = None
        for participant in job_ctx.room.remote_participants.values():
            if participant.identity == "sip-caller":
                sip_participant = participant
                break

        if not sip_participant:
            logger.error("No SIP participant found")
            return "error: no sip participant"

        # Format transfer number
        transfer_to = TRANSFER_NUMBER if TRANSFER_NUMBER.startswith("tel:") else f"tel:{TRANSFER_NUMBER}"
        
        try:
            await job_ctx.api.sip.transfer_sip_participant(
                api.TransferSIPParticipantRequest(
                    room_name=job_ctx.room.name,
                    participant_identity=sip_participant.identity,
                    transfer_to=transfer_to,
                    play_dialtone=True
                )
            )
            logger.info(f"Successfully transferred to {transfer_to}")
            return "transferred successfully"
        except Exception as e:
            logger.error(f"Transfer failed: {e}", exc_info=True)
            return f"error: {str(e)}"

    @function_tool
    async def end_call(self, ctx: RunContext, reason: str = "") -> str:
        """
        End the call gracefully.
        
        Args:
            reason: Optional reason for ending the call
            
        Returns:
            Status of the end call operation
        """
        logger.info(f"End call requested. Reason: {reason}")
        
        job_ctx = get_job_context()
        if not job_ctx:
            logger.error("Job context not found")
            return "error: no job context"

        try:
            await job_ctx.api.room.delete_room(
                api.DeleteRoomRequest(room=job_ctx.room.name)
            )
            logger.info(f"Call ended for room {job_ctx.room.name}")
            return "call ended"
        except Exception as e:
            logger.error(f"Failed to end call: {e}", exc_info=True)
            return f"error: {str(e)}"


# ------------------------------------------------------------
# Agent Entrypoint
# ------------------------------------------------------------
async def entrypoint(ctx: agents.JobContext):
    """Main entrypoint for the outbound agent."""
    
    logger.info("=" * 60)
    logger.info(f"NEW CALL - Agent joining room: {ctx.room.name}")
    logger.info("=" * 60)

    # Setup cleanup callback
    async def cleanup_and_save():
        """Save transcript and cleanup resources."""
        try:
            logger.info("Cleanup started...")
            await asyncio.sleep(1.0)  # Allow graceful closure
            
            # Save transcript if session exists
            if "session" in locals() and session and hasattr(session, "history"):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                room_safe = ctx.room.name.replace("/", "-")
                filename = TRANSCRIPT_DIR / f"transcript_{room_safe}_{timestamp}.json"
                
                with open(filename, "w") as f:
                    json.dump(session.history.to_dict(), f, indent=2)
                logger.info(f"Transcript saved to {filename}")
            
            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}", exc_info=True)

    ctx.add_shutdown_callback(cleanup_and_save)

    # Initialize components
    try:
        logger.info("Initializing speech components...")
        
        # Speech-to-Text (Deepgram)
        stt = deepgram.STT(model=STT_MODEL, language=STT_LANGUAGE)
        logger.info("✓ STT initialized (Deepgram)")
        
        # Large Language Model (OpenAI)
        llm = openai.LLM(model=LLM_MODEL)
        logger.info("✓ LLM initialized (OpenAI)")
        
        # Text-to-Speech (ElevenLabs)
        try:
            tts = elevenlabs.TTS(
                voice_id=TTS_VOICE_ID,
                language=TTS_LANGUAGE,
                model="eleven_multilingual_v2"
            )
            logger.info("✓ TTS initialized (ElevenLabs)")
        except Exception as e:
            logger.warning(f"ElevenLabs failed, using OpenAI TTS: {e}")
            tts = openai.TTS(voice="alloy", model="tts-1")
            logger.info("✓ TTS initialized (OpenAI fallback)")
        
        # Create session
        session = AgentSession(stt=stt, llm=llm, tts=tts)
        logger.info("✓ Agent session created")
        
    except Exception as e:
        logger.error(f"Component initialization failed: {e}", exc_info=True)
        raise

    # Connect to room
    try:
        logger.info(f"Connecting to room: {ctx.room.name}")
        await ctx.connect()
        logger.info("✓ Connected to room")
    except Exception as e:
        logger.error(f"Room connection failed: {e}", exc_info=True)
        raise

    # Start agent session
    assistant = OutboundAssistant()
    room_options = RoomInputOptions(
        noise_cancellation=noise_cancellation.BVC()
    )

    try:
        logger.info("Starting agent session...")
        await session.start(
            room=ctx.room,
            agent=assistant,
            room_input_options=room_options
        )
        logger.info("✓ Agent session started")
    except Exception as e:
        logger.error(f"Session start failed: {e}", exc_info=True)
        await ctx.shutdown()
        raise

    # Wait for caller to join before greeting
    logger.info("Waiting for caller to join...")
    await asyncio.sleep(3)  # Give SIP participant time to connect
    
    # Check if SIP participant has joined
    sip_joined = False
    for participant in ctx.room.remote_participants.values():
        if participant.identity == "sip-caller":
            sip_joined = True
            logger.info(f"✓ SIP caller joined: {participant.name}")
            break
    
    if not sip_joined:
        logger.warning("No SIP caller detected yet, but proceeding with greeting")
    
    # Send greeting
    greeting = (
        "Hello! This is an automated call from your assistant. "
        "How can I help you today?"
    )
    
    try:
        await session.generate_reply(instructions=greeting)
        logger.info("✓ Greeting sent")
    except Exception as e:
        logger.error(f"Greeting failed: {e}", exc_info=True)

    # Wait for termination
    logger.info("Call active - waiting for termination...")
    try:
        await ctx.wait_for_termination()
        logger.info("Call ended - termination signal received")
    except asyncio.CancelledError:
        logger.info("Session cancelled")
    except Exception as e:
        logger.error(f"Error during session: {e}", exc_info=True)
    finally:
        await asyncio.sleep(0.5)  # Allow cleanup
        logger.info("=" * 60)
        logger.info(f"CALL COMPLETED - Room: {ctx.room.name}")
        logger.info("=" * 60)


# ------------------------------------------------------------
# CLI Runner
# ------------------------------------------------------------
def run_agent():
    """Run the outbound agent worker."""
    
    logger.info("=" * 60)
    logger.info("Starting Outbound Agent Worker")
    logger.info("=" * 60)
    
    try:
        worker_options = agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name=AGENT_NAME,
            # request_fnc=None means auto-join ALL rooms
        )
        
        logger.info(f"Worker: {AGENT_NAME}")
        logger.info("Mode: Auto-join all rooms (for outbound calls)")
        logger.info("Listening for new rooms...")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 60)
        
        agents.cli.run_app(worker_options)
        
    except KeyboardInterrupt:
        logger.info("Agent stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    run_agent()