import telebot
import requests
import google.generativeai as genai
import os
from flask import Flask
from threading import Thread

# --- 1. МИНИ-СЕРВЕР ДЛЯ RENDER (ЧТОБЫ НЕ СПАЛ) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    # Render автоматически подставляет PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. НАСТРОЙКИ И КЛЮЧИ ---
# На Render лучше добавить их в Environment Variables, но можно и вписать сюда
TOKEN = '8624691803:AAHONwvZ3e6A99Aac-JjwEdUvJgpqiqM1m0'
FOOTBALL_API_KEY = 'f2539298091241a187bf9394eb390ab7'
GEMINI_KEY = 'AIzaSyCOIl0BBdAMb2qFpfC3mhWQ71etG8wPMXI'

# Настройка Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

bot = telebot.TeleBot(TOKEN)
headers = {'X-Auth-Token': FOOTBALL_API_KEY}

# --- 3. ЛОГИКА ПРОГНОЗА ---
def get_ai_prediction(home, away, league):
    prompt = f"Ты футбольный эксперт. Дай краткий, дерзкий прогноз на матч {home} vs {away} ({league}). Кто победит и примерный счет? Пиши на русском, 3 предложения, используй эмодзи."
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Ошибка Gemini: {e}")
        return "🤖 Нейросеть призадумалась... Но по статистике нас ждет потная игра! ⚽️"

def get_match_data(team_query):
    try:
        res = requests.get("https://api.football-data.org/v4/matches", headers=headers).json()
        matches = res.get('matches', [])
    except:
        return "⚠️ Ошибка связи с футбольным сервером.", ""
    
    query = team_query.lower()
    for m in matches:
        home = m['homeTeam']['name']
        away = m['awayTeam']['name']
        
        if query in home.lower() or query in away.lower():
            league = m['competition']['name']
            # Получаем крутой прогноз от ИИ
            analysis = get_ai_prediction(home, away, league)
            
            text = f"🏟 **Матч:** {home} vs {away}\n🏆 **Лига:** {league}\n\n"
            text += f"🧠 **Аналитика от Gemini:**\n{analysis}"
            return text, m['homeTeam']['crest']
            
    return f"🤷‍♂️ Матч для '{team_query}' на ближайшее время не найден.", ""

# --- 4. ОБРАБОТКА КОМАНД ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Салам! Напиши название команды (напр. Chelsea), и я выдам ИИ-прогноз! 🤖⚽️")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        msg = bot.reply_to(message, "⏳ Нейросеть изучает тактику...")
        result_text, logo = get_match_data(message.text)
        
        if logo:
            bot.send_photo(message.chat.id, logo, caption=result_text, parse_mode='Markdown')
            bot.delete_message(message.chat.id, msg.message_id)
        else:
            bot.edit_message_text(result_text, message.chat.id, msg.message_id)
    except Exception as e:
        bot.reply_to(message, "⚠️ Ошибка. Попробуй позже.")
        print(f"Bot Error: {e}")

# --- 5. ЗАПУСК ---
if __name__ == "__main__":
    keep_alive() # Запускаем веб-сервер для "прозвона"
    print("✅ Бот запущен на Render!")
    bot.infinity_polling()
