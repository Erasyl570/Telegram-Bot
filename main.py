import threading
import os
from flask import Flask
from telegram_bot import run_bot

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

def start_bot():
    run_bot()

if __name__ == "__main__":
    
    # запускаем бота в отдельном потоке
    threading.Thread(target=start_bot).start()

    # открываем порт для Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
