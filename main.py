import os
import logging
import time
from threading import Thread
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Спасательный круг для Render
app = Flask('')
@app.route('/')
def home():
    return "Бот жив и готов искать матчи!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def main():
    logger.info("Запуск веб-сервера для Render...")
    Thread(target=run_web).start()
    
    logger.info("Запуск Telegram-бота...")
    time.sleep(3)
    
    from telegram_bot import run_bot
    run_bot()

if __name__ == "__main__":
    main()
