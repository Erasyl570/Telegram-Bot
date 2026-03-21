import telebot
import requests
import os
from flask import Flask
from threading import Thread

# --- СЕРВЕР ---
app = Flask('')
@app.route('/')
def home(): return "Бот в сети!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run).start()

# --- КОНФИГ (Твой токен уже тут) ---
TOKEN = '8624691803:AAHBjvIvM8qUNwSY9wrkzAXu44BiiiICe9U'
FOOTBALL_API_KEY = 'f2539298091241a187bf9394eb390ab7'
HF_TOKEN = "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"

bot = telebot.TeleBot(TOKEN)

# --- ПРОГНОЗ (Исправленный адрес API) ---
def get_ai_prediction(home, away, league):
    prompt = f"Ты футбольный аналитик. Кратко на русском (2 предложения): кто победит в матче {home} - {away} ({league}) и какой примерный счет?"
    # Тот самый новый адрес, который просил Hugging Face
    api_url = "https://router.huggingface.co/hf-inference/models/Qwen/Qwen2.5-7B-Instruct"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    try:
        response = requests.post(api_url, headers=headers, json={
            "inputs": prompt,
            "parameters": {"max_new_tokens": 100}
        }, timeout=15)
        result = response.json()
        
        if isinstance(result, list) and len(result) > 0:
            text = result[0].get('generated_text', "").replace(prompt, "").strip()
            return text if text else "🤖 Аналитика будет готова через минуту!"
        return "🤖 Нейросеть настраивается, попробуй еще раз!"
    except:
        return "🤖 Прогноз временно недоступен, но игра будет мощной!"

# --- ЛОГИКА МАТЧЕЙ ---
def get_match_data(team_query):
    headers = {'X-Auth-Token': FOOTBALL_API_KEY}
    try:
        res = requests.get("https://api.football-data.org/v4/matches", headers=headers, timeout=10).json()
        matches = res.get('matches', [])
    except:
        return "⚠️ Ошибка футбольного API.", ""
    
    q = team_query.lower()
    for m in matches:
        h, a = m['homeTeam']['name'], m['awayTeam']['name']
        if q in h.lower() or q in a.lower():
            analysis = get_ai_prediction(h, a, m['competition']['name'])
            text = f"🏟 **Матч:** {h} vs {a}\n🏆 **Лига:** {m['competition']['name']}\n\n🧠 **Прогноз:**\n{analysis}"
            return text, m['homeTeam']['crest']
    return f"🤷‍♂️ Матч для '{team_query}' не найден.", ""

# --- ОБРАБОТКА ---
@bot.message_handler(commands=['start'])
def welcome(m):
    bot.reply_to(m, "Салам! Напиши команду (напр. Chelsea) — и я дам прогноз!")

@bot.message_handler(func=lambda m: True)
def handle(m):
    status = bot.reply_to(m, "⏳ Анализирую...")
    text, logo = get_match_data(m.text)
    if logo:
        bot.send_photo(m.chat.id, logo, caption=text, parse_mode='Markdown')
        bot.delete_message(m.chat.id, status.message_id)
    else:
        bot.edit_message_text(text, m.chat.id, status.message_id)

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
