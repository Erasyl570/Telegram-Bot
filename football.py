import telebot, requests, os, time
from flask import Flask
from threading import Thread

app = Flask('')
@app.route('/')
def home(): return "Бот в сети"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- КОНФИГ ---
TOKEN = '8624691803:AAHBjvIvM8qUNwSY9wrkzAXu44BiiiICe9U'
FOOTBALL_API_KEY = 'f2539298091241a187bf9394eb390ab7'
HF_TOKEN = "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"

bot = telebot.TeleBot(TOKEN)

def get_ai_prediction(home, away, league):
    url = "https://router.huggingface.co/hf-inference/models/mistralai/Mistral-7B-Instruct-v0.3"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    prompt = f"<s>[INST] Ты футбольный аналитик. Кто победит в матче {home} - {away} ({league})? Дай краткий прогноз и счет на русском. [/INST]"
    
    try:
        # Увеличил таймаут до 30 секунд, чтобы дать ИИ проснуться
        res = requests.post(url, headers=headers, json={"inputs": prompt, "parameters": {"max_new_tokens": 100}}, timeout=30)
        data = res.json()
        if isinstance(data, list):
            return data[0]['generated_text'].split("[/INST]")[-1].strip()
        return "⚠️ ИИ перегружен, попробуй через минуту."
    except:
        return "⚠️ Ошибка связи с ИИ."

@bot.message_handler(func=lambda m: True)
def handle(m):
    # Поиск матча
    res = requests.get("https://api.football-data.org/v4/matches", headers={'X-Auth-Token': FOOTBALL_API_KEY}).json()
    for match in res.get('matches', []):
        h, a = match['homeTeam']['name'], match['awayTeam']['name']
        if m.text.lower() in h.lower() or m.text.lower() in a.lower():
            bot.reply_to(m, "⏳ Запрашиваю реальный ИИ...")
            pred = get_ai_prediction(h, a, match['competition']['name'])
            bot.send_photo(m.chat.id, match['homeTeam']['crest'], caption=f"🏟 {h} vs {a}\n\n🧠 Прогноз:\n{pred}")
            return
    bot.reply_to(m, "Матч не найден.")

if __name__ == "__main__":
    Thread(target=run).start()
    bot.remove_webhook()
    time.sleep(2)
    bot.infinity_polling()
