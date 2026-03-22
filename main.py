import os
import logging
from pathlib import Path
from dotenv import load_dotenv
import time

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting Football Prediction Bot...")
    
    # Ждём 5 секунд чтобы старый инстанс завершился
    time.sleep(5)
    
    from telegram_bot import run_bot
    run_bot()

if __name__ == "__main__":
    main()
