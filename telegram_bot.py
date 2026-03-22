import os
import time
import logging
import requests
from threading import Thread
from flask import Flask
import telebot
import google.generativeai as genai

# --- 1. ФЛАСК СЕРВЕР ДЛЯ RENDER (ЧТОБЫ БОТ ЖИЛ МЕСЯЦАМИ) ---
app = Flask('')
@app.route('/')
def home(): 
    return "Бот работает и готов к прогнозам!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    Thread(target=run_flask).start()

# --- 2. НАСТРОЙКА ЛОГОВ И КЛЮЧЕЙ ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Render берет эти ключи из вкладки Environment Variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
FOOTBALL_API_KEY = os.getenv('FOOTBALL_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# --- 3. ПОЛУЧЕНИЕ ПРОГНОЗА ОТ ИИ (GEMINI) ---
def get_ai_prediction(home, away, league):
    if not GEMINI_API_KEY:
        return "⚠️ Ошибка: Ключ Gemini не найден."
        
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Ты футбольный эксперт. Проанализируй матч {home} - {away} ({league}). Кто победит и какой примерный счет? Напиши 2 предложения на русском и без значков по типу * ."
        
        # Простой и надежный синхронный запрос
        response = model.generate_content(prompt)
        return response.text.replace('*', '').strip()
    except Exception as e:
        logger.error(f"Ошибка ИИ: {e}")
        return "⚠️ Робот-аналитик перегружен. Попробуй еще раз через минуту."

# --- 4. ПОИСК МАТЧЕЙ (БЕЗОПАСНО ДЛЯ БЕСПЛАТНОГО ТАРИФА) ---
def get_match_data(team_query):
    headers = {'X-Auth-Token': FOOTBALL_API_KEY}
    try:
        # Один безопасный запрос ко всем текущим матчам
        res = requests.get("https://api.football-data.org/v4/matches", headers=headers, timeout=10).json()
        matches = res.get('matches', [])
    except Exception as e:
        logger.error(f"Ошибка API футбола: {e}")
        return None, None, None, None

    q = team_query.lower()
    for m in matches:
        h, a = m['homeTeam']['name'], m['awayTeam']['name']
        if q in h.lower() or q in a.lower():
            return m, h, a, m['homeTeam']['crest']
    return None, None, None, None

# --- 5. ОБРАБОТКА СООБЩЕНИЙ В ТЕЛЕГРАМЕ ---
@bot.message_handler(commands=['start', 'help'])
def handle_start(message):
    bot.reply_to(message, "👋 Привет! Напиши название команды на английском, и я выдам прогноз.")

@bot.message_handler(func=lambda m: True)
def handle_team_search(message):
    status = bot.reply_to(message, "⏳ Ищу матч в базе данных...")
    
    match, home, away, crest_url = get_match_data(message.text)
    
    if not match:
        bot.edit_message_text(f"❌ Матчи для '{message.text}' не найдены.", message.chat.id, status.message_id)
        return

    comp = match['competition']['name']
    
    bot.edit_message_text("✅ Матч найден! Генерирую прогноз Gemini (это займет пару секунд)...", message.chat.id, status.message_id)
    
    prediction = get_ai_prediction(home, away, comp)
    text = f"🏟 **Матч:** {home} vs {away}\n🏆 **Лига:** {comp}\n\n🤖 **Прогноз Gemini:**\n{prediction}"
    
    try:
        bot.send_photo(message.chat.id, crest_url, caption=text, parse_mode='Markdown')
        bot.delete_message(message.chat.id, status.message_id)
    except:
        bot.edit_message_text(text, message.chat.id, status.message_id, parse_mode='Markdown')

if __name__ == "__main__":
    keep_alive()
    bot.remove_webhook()
    time.sleep(2)
    logger.info("✅ БОТ ГОТОВ К РАБОТЕ!")
    bot.infinity_polling(timeout=20, long_polling_timeout=5)
