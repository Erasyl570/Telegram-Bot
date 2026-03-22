import threading
from telegram_bot import run_bot
from web import app
import os

def start_bot():
    run_bot()

if __name__ == "__main__":
    threading.Thread(target=start_bot).start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
