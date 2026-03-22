"""
Main entry point for the Football Prediction Telegram Bot
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=" * 50)
    logger.info("Starting Football Prediction Bot...")
    logger.info("=" * 50)
    
    from keep_alive import keep_alive
    keep_alive()
    
    from telegram_bot import run_bot
    run_bot()


if __name__ == "__main__":
    main()
