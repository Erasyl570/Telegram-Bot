import telebot
import requests
import os
from flask import Flask
from threading import Thread

# --- 1. СЕРВЕР ДЛЯ ПОДДЕРЖКИ ЖИЗНИ (RENDER) ---
app = Flask('')

@app.route('/')
def home():
    return "Бот работает и готов к прогнозам!"

def run():
    # Render сам назначит порт, берем его из системы
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. НАСТРОЙКИ И КЛЮЧИ ---
# ВАЖНО: Вставь сюда НОВЫЙ токен от BotFather!
TOKEN = 'ТВОЙ_НОВЫЙ_ТОКЕН_ИЗ_BOTFATHER' 
FOOTBALL_API_KEY = 'f2539298091241a187bf9394eb390ab7'
HF_TOKEN = "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"

bot = telebot.TeleBot(TOKEN)

# --- 3. РАБОТА С НЕЙРОСЕТЬЮ (Hugging Face) ---
def get_ai_prediction(home, away, league):
    # Промпт для модели Qwen 2.5
    prompt = f"Ты эксперт футбола. Дай краткий прогноз на матч {home} - {away} ({league}). Кто победит и какой счет? Ответь на русском, 2 предложения."
    
    # Используем модель Qwen 2.5 — она умнее и быстрее Mistral
    api_url = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-7B-Instruct"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    try:
        response = requests.post(api_url, headers=headers, json={
            "inputs": prompt,
            "parameters": {"max_new_tokens": 150, "temperature": 0.7}
        }, timeout=15)
        result = response.json()
        
        # Печать ответа в консоль Render для отладки
        print(f"AI Response: {result}")
        
        if isinstance(result, list) and 'generated_text' in result[0]:
            text = result[0]['generated_text'].replace(prompt, "").strip()
            return text if text else "🤖 Хм, нейросеть задумалась. Попробуй еще раз через минуту!"
            
        elif isinstance(result, dict) and 'error' in result:
            if "loading" in result['error'].lower():
                return "🤖 Нейросеть просыпается (загрузка модели)... Подожди 20 секунд и попробуй снова!"
            return f"⚠️ Ошибка ИИ: {result['error']}"
            
        return "🤖 Статистика говорит, что нас ждет плотный матч! Ждем борьбу."
    except Exception as e:
        return f"🔌 Сбой связи с ИИ: {e}"

# --- 4. ПОЛУЧЕНИЕ ДАННЫХ О МАТЧЕ ---
def get_match_data(team_query):
    headers = {'X-Auth-Token': FOOTBALL_API_KEY}
    try:
        # Берем список ближайших матчей
        res = requests.get("https://api.football-data.org/v4/matches", headers=headers, timeout=10).json()
        matches = res.get('matches', [])
    except Exception as e:
        return f"⚠️ Ошибка футбольного API: {e}", ""
    
    query = team_query.lower()
    for m in matches:
        h_name = m['homeTeam']['name']
        a_name = m['awayTeam']['name']
        
        # Поиск совпадения по названию команды
        if query in h_name.lower() or query in a_name.lower():
            league = m['competition']['name']
            analysis = get_ai_prediction(h_name, a_name, league)
            
            res_text = (
                f"🏟 **Матч:** {h_name} vs {a_name}\n"
                f"🏆 **Лига:** {league}\n\n"
                f"🧠 **ИИ Прогноз:**\n{analysis}"
            )
            return res_text, m['homeTeam']['crest']
            
    return f"🤷‍♂️ Матч для '{team_query}' на ближайшие дни не найден.", ""

# --- 5. ОБРАБОТКА СООБЩЕНИЙ ---
@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "Салам! Напиши команду (напр. Real Madrid), и я проанализирую их следующий матч! ⚽️🤖")

@bot.message_handler(func=lambda m: True)
def handle_text(m):
    status_msg = bot.reply_to(m, "⏳ Связываюсь с нейросетью...")
    text, logo = get_match_data(m.text)
    
    if logo:
        bot.send_photo(m.chat.id, logo, caption=text, parse_mode='Markdown')
        bot.delete_message(m.chat.id, status_msg.message_id)
    else:
        bot.edit_message_text(text, m.chat.id, status_msg.message_id)

# --- 6. ЗАПУСК ---
if __name__ == "__main__":
    keep_alive() # Запуск Flask для Render
    print("✅ БОТ ОФИЦИАЛЬНО ЗАПУЩЕН!")
    bot.infinity_polling()
