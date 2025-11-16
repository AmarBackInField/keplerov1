import logging
import sys
from services.agent_service import run_agent

# Setup basic logging before running
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('entry_debug.log')
    ]
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("ENTRY POINT - Starting Application")
    logger.info(f"Command line args: {sys.argv}")
    logger.info("=" * 60)
    try:
        # Run the agent worker - it will keep running until interrupted
        logger.info("Starting agent worker (will run continuously)...")
        run_agent()
    except KeyboardInterrupt:
        logger.info("Agent worker stopped by user (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        sys.exit(1)