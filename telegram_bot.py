import os
import logging
import threading
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path

import telebot
import google.generativeai as genai

# === LOAD ENV ===
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# === LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# === TOKENS ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("Нет TELEGRAM_BOT_TOKEN")

if not FOOTBALL_API_KEY:
    raise ValueError("Нет FOOTBALL_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("Нет GEMINI_API_KEY")

# === INIT ===
bot = telebot.TeleBot(TELEGRAM_TOKEN)

genai.configure(api_key=GEMINI_API_KEY)

FOOTBALL_API_URL = "https://api.football-data.org/v4"


# ===================== FOOTBALL =====================

def get_headers():
    return {"X-Auth-Token": FOOTBALL_API_KEY}


def search_team_matches(team_name: str):

    try:

        competitions = ["PL", "PD", "BL1", "SA", "FL1"]

        team_name_lower = team_name.lower()

        found_team = None

        for comp in competitions:

            url = f"{FOOTBALL_API_URL}/competitions/{comp}/teams"

            response = requests.get(url, headers=get_headers(), timeout=10)

            if response.status_code != 200:
                continue

            for team in response.json().get("teams", []):

                if team_name_lower in team["name"].lower():

                    found_team = team
                    break

            if found_team:
                break

        if not found_team:
            return None

        team_id = found_team["id"]

        date_from = datetime.now().strftime("%Y-%m-%d")

        date_to = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

        url = f"{FOOTBALL_API_URL}/teams/{team_id}/matches"

        params = {
            "dateFrom": date_from,
            "dateTo": date_to,
            "status": "SCHEDULED"
        }

        response = requests.get(
            url,
            headers=get_headers(),
            params=params,
            timeout=10
        )

        if response.status_code != 200:
            return None

        matches = response.json().get("matches", [])

        if not matches:
            return {"team": found_team, "match": None}

        return {"team": found_team, "match": matches[0]}

    except Exception as e:

        logger.error(f"Football API error: {e}")

        return None


# ===================== GEMINI =====================

def get_prediction(home, away, league):

    try:

        model = genai.GenerativeModel("gemini-2.5-flash")

        prompt = f"""
Ты футбольный аналитик.

Матч:
{home} vs {away}
Турнир: {league}

Сделай краткий прогноз.

Напиши:
1) Кто победит
2) Примерный счет
3) Короткое объяснение (1-2 предложения)

Пиши на русском и без знаков по типу **
"""

        logger.info("Запрос к Gemini")

        response = model.generate_content(prompt)

        if not response.text:
            return None

        logger.info("Ответ от Gemini получен")

        return response.text.strip()

    except Exception as e:

        logger.error(f"Gemini error: {e}")

        return None


# ===================== THREAD =====================

def generate_and_send(chat_id, message_id, home, away, league, date):

    prediction = get_prediction(home, away, league)

    text = f"""⚽ {home} vs {away}

🏆 {league}
📅 {date}

🤖 Прогноз:

{prediction if prediction else "❌ Не удалось получить прогноз. Попробуйте позже."}
"""

    try:

        bot.edit_message_text(text, chat_id, message_id)

    except Exception as e:

        logger.error(f"Telegram edit error: {e}")


# ===================== HANDLERS =====================

@bot.message_handler(commands=["start"])
def start(message):

    bot.reply_to(
        message,
        "👋 Напиши название команды\n\nПример:\nBarcelona\nChelsea\nBayern"
    )


@bot.message_handler(func=lambda m: True)
def handle(message):

    team = message.text.strip()

    msg = bot.reply_to(message, f"🔍 Ищу матчи для {team}...")

    data = search_team_matches(team)

    if not data:

        bot.edit_message_text(
            "❌ Команда не найдена",
            message.chat.id,
            msg.message_id
        )

        return

    match = data.get("match")

    if not match:

        bot.edit_message_text(
            "❌ Нет ближайших матчей",
            message.chat.id,
            msg.message_id
        )

        return

    home = match["homeTeam"]["name"]

    away = match["awayTeam"]["name"]

    league = match["competition"]["name"]

    date = match["utcDate"][:10]

    bot.edit_message_text(
        "⏳ Генерирую прогноз...",
        message.chat.id,
        msg.message_id
    )

    threading.Thread(
        target=generate_and_send,
        args=(message.chat.id, msg.message_id, home, away, league, date)
    ).start()


# ===================== RUN =====================

def run_bot():

    logger.info("🚀 Bot started")

    bot.infinity_polling(timeout=60, long_polling_timeout=60)
