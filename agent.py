import os
import logging
import sys
import asyncio
from pathlib import Path

from livekit.agents import (
    cli,
    WorkerOptions,
    JobContext,
    AgentSession,
    function_tool,
    RunContext,
)
from livekit.agents.voice import Agent
from livekit.plugins import deepgram, openai, elevenlabs, silero, google

from dotenv import load_dotenv
load_dotenv()

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from RAGService import RAGService

# ------------------------------------------------------------
# Environment variables
# ------------------------------------------------------------
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

# ---------------- Logging ---------------- #
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("livekit-agent")

# ------------------------------------------------------------
# Agent Instructions
# ------------------------------------------------------------
AGENT_INSTRUCTIONS = """You are a helpful voice AI assistant.

When users ask questions, use the knowledge_base_search tool to find relevant information, then naturally incorporate that information into your conversational response. Speak naturally and fluidly as if the information is part of your knowledge.

Be conversational, friendly, and helpful in your responses."""

# ------------------------------------------------------------
# Custom Agent with Tools
# ------------------------------------------------------------
class MyAssistant(Agent):
    def __init__(self):
        # Initialize RAG service with environment variables
        try:
            openai_api_key = os.getenv("OPENAI_API_KEY")
            
            self.rag_service = RAGService(
                openai_api_key=openai_api_key
                )
            logger.info("✓ RAG service initialized")
        except Exception as e:
            logger.error(f"RAG service initialization failed: {e}", exc_info=True)
            self.rag_service = None
        
        # Cache for search results
        self.search_cache = {}
        
        super().__init__(instructions=AGENT_INSTRUCTIONS)
    
    async def _perform_search_background(self, query: str):
        """Background task to perform knowledge base search."""
        try:
            logger.info(f"🔍 Background search starting: {query}")
            
            search_results = self.rag_service.retrieval_based_search(
                query=query,
                collections=None,
                top_k=1
            )
            
            if search_results and len(search_results) > 0:
                context_parts = []
                for result in search_results[:3]:
                    text = result.get('text', '').strip()
                    if text:
                        context_parts.append(text)
                
                context_text = "\n\n".join(context_parts)
                self.search_cache[query] = context_text
                logger.info(f"✓ Background search completed: found {len(search_results)} results")
            else:
                logger.info(f"No results found for: {query}")
                self.search_cache[query] = ""
                
        except Exception as e:
            logger.error(f"Background search error: {e}", exc_info=True)
            self.search_cache[query] = ""
    
    @function_tool
    async def knowledge_base_search(self, query: str) -> str:
        """
        Search the knowledge base for relevant information. This function returns immediately
        while the search continues in the background, allowing the agent to start speaking
        without delay.
        
        Args:
            query: The user's question or topic to search for
        """
        logger.info(f"🔍 Knowledge base search requested: {query}")
        
        if not self.rag_service:
            logger.warning("RAG service not available")
            return "Use your general knowledge to answer this question."
        
        # Start background search task
        asyncio.create_task(self._perform_search_background(query))
        
        # Return immediately so agent can start speaking
        logger.info("✓ Search started in background, agent can speak now")
        return "Answer based on your knowledge. Additional details may be available from the knowledge base."

# ---------------- Entrypoint ---------------- #
async def entrypoint(ctx: JobContext):
    logger.info("🚀 Agent starting...")

    # 1️⃣ Connect to room FIRST
    await ctx.connect()
    logger.info("🔗 Connected to LiveKit room")

    # ---------------- STT ---------------- #
    stt = deepgram.STT(
        model="nova-2-general",
        language="en",
    )
    logger.info("✓ STT initialized (Deepgram)")

    # ---------------- LLM ---------------- #
    # llm = openai.LLM(
    #     model="gpt-5-nano",
    # )
    llm = google.LLM(
        model="gemini-2.5-flash-lite",
        api_key=os.getenv("GOOGLE_API_KEY"),
    )
    logger.info("✓ LLM initialized (gemini-2.5-flash-lite)")

    # ---------------- TTS ---------------- #
    tts = elevenlabs.TTS(
        base_url="https://api.eu.residency.elevenlabs.io/v1",
        voice_id="TxGEqnHWrfWFTfGW9XjX",
        api_key=os.getenv("ELEVEN_API_KEY"),
        model="eleven_flash_v2_5",
        language="en",
        streaming_latency=4

    )
    logger.info("✓ TTS initialized (ElevenLabs)")

    # ---------------- VAD ---------------- #
    vad = silero.VAD.load()
    logger.info("✓ VAD initialized (Silero)")

    # ---------------- Voice Agent ---------------- #
    assistant = MyAssistant()
    logger.info("🤖 Agent created with knowledge base tool")

    # ---------------- Agent Session ---------------- #
    session = AgentSession(
        vad=vad,
        stt=stt,
        llm=llm,
        tts=tts,
    )
    logger.info("📋 Session created")

    # 2️⃣ Start session
    await session.start(
        room=ctx.room,
        agent=assistant
    )

    logger.info("✅ Agent started successfully")

# ---------------- Worker ---------------- #
if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )
