"""
Telegram Bot для футбольных прогнозов
"""

import os
import asyncio
import logging
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path

import telebot
from telebot.types import Message

import google.generativeai as genai

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
FOOTBALL_API_KEY = os.getenv('FOOTBALL_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден")
if not FOOTBALL_API_KEY:
    raise ValueError("FOOTBALL_API_KEY не найден")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY не найден")

genai.configure(api_key=GEMINI_API_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

try:
    bot.remove_webhook()
    logger.info("Webhook removed")
except Exception as e:
    logger.warning(f"Could not remove webhook: {e}")

FOOTBALL_API_URL = "https://api.football-data.org/v4"

def get_football_headers():
    return {"X-Auth-Token": FOOTBALL_API_KEY}

def search_team_matches(team_name: str):
    try:
        competitions = ["PL", "PD", "BL1", "SA", "FL1", "CL", "EL"]
        team_name_lower = team_name.lower()
        found_team = None
        
        for comp in competitions:
            try:
                url = f"{FOOTBALL_API_URL}/competitions/{comp}/teams"
                response = requests.get(url, headers=get_football_headers(), timeout=10)
                if response.status_code == 200:
                    for team in response.json().get("teams", []):
                        if team_name_lower in team.get("name", "").lower() or \
                           team_name_lower in team.get("shortName", "").lower():
                            found_team = team
                            break
                if found_team:
                    break
            except:
                continue
        
        if not found_team:
            return None
        
        team_id = found_team.get("id")
        matches_url = f"{FOOTBALL_API_URL}/teams/{team_id}/matches"
        
        date_from = datetime.now().strftime("%Y-%m-%d")
        date_to = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        params = {"dateFrom": date_from, "dateTo": date_to, "status": "SCHEDULED,TIMED"}
        response = requests.get(matches_url, headers=get_football_headers(), params=params, timeout=10)
        
        if response.status_code != 200:
            return None
        
        matches = response.json().get("matches", [])
        
        if not matches:
            return {"team": found_team, "match": None}
        
        return {"team": found_team, "match": matches[0]}
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return None

async def get_ai_prediction(team_a: str, team_b: str, competition: str):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""Ты футбольный эксперт. Проанализируй матч:
{team_a} vs {team_b}, {competition}

Кратко: кто победит, счёт, почему (1-2 предложения). На русском без специальных значков типо * ."""
        
        response = await asyncio.wait_for(
            asyncio.to_thread(model.generate_content, prompt),
            timeout=15.0
        )
        return response.text
    except:
        return None

@bot.message_handler(commands=['start', 'help'])
def handle_start(message):
    bot.reply_to(message, """👋 Привет! Я бот для футбольных прогнозов.

⚽ Напиши название команды (Barcelona, Chelsea, Bayern) — дам прогноз на ближайший матч.""")

@bot.message_handler(func=lambda m: True)
def handle_team_search(message):
    team_name = message.text.strip()
    if len(team_name) < 2:
        bot.reply_to(message, "⚠️ Введите название команды.")
        return
    
    msg = bot.reply_to(message, f"🔍 Ищу матчи для '{team_name}'...")
    
    try:
        match_data = search_team_matches(team_name)
        
        if not match_data:
            bot.edit_message_text(f"❌ Команда '{team_name}' не найдена.", message.chat.id, msg.message_id)
            return
        
        match = match_data.get("match")
        if not match:
            bot.edit_message_text("❌ Ближайших матчей не найдено.", message.chat.id, msg.message_id)
            return
        
        home = match["homeTeam"]["name"]
        away = match["awayTeam"]["name"]
        comp = match["competition"]["name"]
        date = match.get("utcDate", "")[:10]
        
        bot.edit_message_text("✅ Генерирую прогноз...", message.chat.id, msg.message_id)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        prediction = loop.run_until_complete(get_ai_prediction(home, away, comp))
        loop.close()
        
        text = f"""⚽ {home} vs {away}
🏆 {comp}
📅 {date}

🤖 Прогноз:
{prediction or "Робот-аналитик взял перерыв, попробуйте снова."}"""
        
        bot.edit_message_text(text, message.chat.id, msg.message_id)
    except Exception as e:
        logger.error(f"Error: {e}")
        bot.edit_message_text("❌ Ошибка. Попробуйте позже.", message.chat.id, msg.message_id)

def run_bot():
    logger.info("Starting bot...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)

if __name__ == "__main__":
    run_bot()
