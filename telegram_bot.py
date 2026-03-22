Action: file_editor view /app/backend/telegram_bot.py
Observation: [Showing lines 1-378 of 378 total] /app/backend/telegram_bot.py:
1|"""
2|Telegram Bot для футбольных прогнозов
3|Использует football-data.org API и Google Gemini для генерации прогнозов
4|"""
5|
6|import os
7|import asyncio
8|import logging
9|import requests
10|from datetime import datetime, timedelta
11|from dotenv import load_dotenv
12|from pathlib import Path
13|
14|import telebot
15|from telebot.types import Message
16|
17|import google.generativeai as genai
18|
19|# Load environment variables
20|ROOT_DIR = Path(__file__).parent
21|load_dotenv(ROOT_DIR / '.env')
22|
23|# Configure logging
24|logging.basicConfig(
25|    level=logging.INFO,
26|    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
27|)
28|logger = logging.getLogger(__name__)
29|
30|# Get tokens from environment
31|TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
32|FOOTBALL_API_KEY = os.getenv('FOOTBALL_API_KEY')
33|GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
34|
35|if not TELEGRAM_TOKEN:
36|    raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
37|if not FOOTBALL_API_KEY:
38|    raise ValueError("FOOTBALL_API_KEY не найден в переменных окружения")
39|if not GEMINI_API_KEY:
40|    raise ValueError("GEMINI_API_KEY не найден в переменных окружения")
41|
42|# Configure Gemini
43|genai.configure(api_key=GEMINI_API_KEY)
44|
45|# Initialize bot
46|bot = telebot.TeleBot(TELEGRAM_TOKEN)
47|
48|# Remove webhook to prevent Error 409 (Conflict)
49|try:
50|    bot.remove_webhook()
51|    logger.info("Webhook removed successfully")
52|except Exception as e:
53|    logger.warning(f"Could not remove webhook: {e}")
54|
55|# Football-data.org API base URL
56|FOOTBALL_API_URL = "https://api.football-data.org/v4"
57|
58|
59|def get_football_headers():
60|    """Get headers for football-data.org API"""
61|    return {
62|        "X-Auth-Token": FOOTBALL_API_KEY
63|    }
64|
65|
66|def search_team_matches(team_name: str) -> dict | None:
67|    """
68|    Search for current or upcoming matches for a team
69|    Returns match info or None if not found
70|    """
71|    try:
72|        # First, search for the team
73|        teams_url = f"{FOOTBALL_API_URL}/teams"
74|        params = {"limit": 100}
75|        
76|        response = requests.get(teams_url, headers=get_football_headers(), params=params, timeout=10)
77|        
78|        if response.status_code != 200:
79|            logger.error(f"Failed to fetch teams: {response.status_code}")
80|            return None
81|        
82|        teams_data = response.json()
83|        teams = teams_data.get("teams", [])
84|        
85|        # Find team by name (case-insensitive partial match)
86|        team_name_lower = team_name.lower()
87|        found_team = None
88|        
89|        for team in teams:
90|            if team_name_lower in team.get("name", "").lower() or \
91|               team_name_lower in team.get("shortName", "").lower() or \
92|               team_name_lower in team.get("tla", "").lower():
93|                found_team = team
94|                break
95|        
96|        if not found_team:
97|            # Try searching in competitions
98|            competitions = ["PL", "PD", "BL1", "SA", "FL1", "CL", "EL"]
99|            
100|            for comp in competitions:
101|                try:
102|                    comp_teams_url = f"{FOOTBALL_API_URL}/competitions/{comp}/teams"
103|                    response = requests.get(comp_teams_url, headers=get_football_headers(), timeout=10)
104|                    
105|                    if response.status_code == 200:
106|                        comp_data = response.json()
107|                        for team in comp_data.get("teams", []):
108|                            if team_name_lower in team.get("name", "").lower() or \
109|                               team_name_lower in team.get("shortName", "").lower() or \
110|                               team_name_lower in team.get("tla", "").lower():
111|                                found_team = team
112|                                break
113|                    
114|                    if found_team:
115|                        break
116|                except Exception as e:
117|                    logger.warning(f"Error searching in competition {comp}: {e}")
118|                    continue
119|        
120|        if not found_team:
121|            logger.info(f"Team '{team_name}' not found")
122|            return None
123|        
124|        logger.info(f"Found team: {found_team.get('name')} (ID: {found_team.get('id')})")
125|        
126|        # Get upcoming matches for this team
127|        team_id = found_team.get("id")
128|        matches_url = f"{FOOTBALL_API_URL}/teams/{team_id}/matches"
129|        
130|        # Get matches for next 30 days
131|        date_from = datetime.now().strftime("%Y-%m-%d")
132|        date_to = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
133|        
134|        params = {
135|            "dateFrom": date_from,
136|            "dateTo": date_to,
137|            "status": "SCHEDULED,TIMED,IN_PLAY,PAUSED"
138|        }
139|        
140|        response = requests.get(matches_url, headers=get_football_headers(), params=params, timeout=10)
141|        
142|        if response.status_code != 200:
143|            logger.error(f"Failed to fetch matches: {response.status_code}")
144|            return None
145|        
146|        matches_data = response.json()
147|        matches = matches_data.get("matches", [])
148|        
149|        if not matches:
150|            # Try to get finished matches for context
151|            params["status"] = "FINISHED"
152|            params["dateFrom"] = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
153|            params["dateTo"] = datetime.now().strftime("%Y-%m-%d")
154|            
155|            response = requests.get(matches_url, headers=get_football_headers(), params=params, timeout=10)
156|            
157|            if response.status_code == 200:
158|                matches_data = response.json()
159|                matches = matches_data.get("matches", [])
160|                
161|                if matches:
162|                    # Return the most recent finished match
163|                    match = matches[-1]
164|                    return {
165|                        "team": found_team,
166|                        "match": match,
167|                        "is_finished": True
168|                    }
169|            
170|            return {"team": found_team, "match": None, "is_finished": False}
171|        
172|        # Return the nearest upcoming match
173|        match = matches[0]
174|        return {
175|            "team": found_team,
176|            "match": match,
177|            "is_finished": False
178|        }
179|        
180|    except requests.exceptions.Timeout:
181|        logger.error("Timeout while fetching football data")
182|        return None
183|    except Exception as e:
184|        logger.error(f"Error searching team matches: {e}")
185|        return None
186|
187|
188|async def get_ai_prediction(team_a: str, team_b: str, competition: str) -> str:
189|    """
190|    Get AI prediction for a match using Google Gemini
191|    """
192|    try:
193|        # Initialize Gemini model
194|        model = genai.GenerativeModel('gemini-1.5-flash')
195|        
196|        # Create prediction prompt
197|        prompt = f"""Ты футбольный эксперт-аналитик с глубокими знаниями о командах, их составах, тактике и текущей форме.
198|
199|Проанализируй футбольный матч:
200|{team_a} vs {team_b}
201|Турнир: {competition}
202|
203|Дай краткий прогноз:
204|1. Кто победит (или будет ничья)?
205|2. Примерный счёт
206|3. Почему (1-2 предложения)
207|
208|Отвечай уверенно, как эксперт. Отвечай на русском языке и без лишних значков как * """
209|        
210|        # Generate with timeout
211|        response = await asyncio.wait_for(
212|            asyncio.to_thread(model.generate_content, prompt),
213|            timeout=15.0
214|        )
215|        
216|        return response.text
217|        
218|    except asyncio.TimeoutError:
219|        logger.error("AI prediction timeout")
220|        return None
221|    except Exception as e:
222|        logger.error(f"AI prediction error: {e}")
223|        return None
224|
225|
226|def format_match_message(match_data: dict, prediction: str) -> str:
227|    """Format the match prediction message"""
228|    team = match_data.get("team", {})
229|    match = match_data.get("match")
230|    is_finished = match_data.get("is_finished", False)
231|    
232|    team_name = team.get("name", "Команда")
233|    team_crest = team.get("crest", "")
234|    
235|    if not match:
236|        return f"⚽ {team_name}\n\n❌ К сожалению, ближайших матчей для этой команды не найдено."
237|    
238|    home_team = match.get("homeTeam", {}).get("name", "Хозяева")
239|    away_team = match.get("awayTeam", {}).get("name", "Гости")
240|    competition = match.get("competition", {}).get("name", "Турнир")
241|    competition_emblem = match.get("competition", {}).get("emblem", "")
242|    
243|    # Format date
244|    utc_date = match.get("utcDate", "")
245|    try:
246|        match_date = datetime.fromisoformat(utc_date.replace("Z", "+00:00"))
247|        date_str = match_date.strftime("%d.%m.%Y %H:%M UTC")
248|    except:
249|        date_str = utc_date
250|    
251|    # Build message
252|    if is_finished:
253|        home_score = match.get("score", {}).get("fullTime", {}).get("home", "?")
254|        away_score = match.get("score", {}).get("fullTime", {}).get("away", "?")
255|        
256|        message = f"""⚽ Последний матч
257|
258|🏆 {competition}
259|📅 {date_str}
260|
261|{home_team} {home_score} : {away_score} {away_team}
262|
263|"""
264|    else:
265|        message = f"""⚽ Ближайший матч
266|
267|🏆 {competition}
268|📅 {date_str}
269|
270|🏠 {home_team}
271|🆚
272|✈️ {away_team}
273|
274|"""
275|    
276|    if prediction:
277|        message += f"🤖 Прогноз ИИ:\n\n{prediction}"
278|    else:
279|        message += "❌ Робот-аналитик взял перерыв, попробуйте запросить матч снова."
280|    
281|    return message
282|
283|
284|@bot.message_handler(commands=['start', 'help'])
285|def handle_start(message: Message):
286|    """Handle /start and /help commands"""
287|    welcome_text = """👋 Привет! Я бот для футбольных прогнозов.
288|
289|⚽ Просто напиши название футбольной команды (например: Barcelona, Real Madrid, Manchester United, Everton), и я найду ближайший матч и дам прогноз на него.
290|
291|📊 Прогнозы генерируются с помощью искусственного интеллекта на основе анализа команд.
292|
293|🔍 Поддерживаются команды из топ-5 европейских лиг и еврокубков.
294|
295|Попробуй! Напиши название любимой команды 👇"""
296|    
297|    bot.reply_to(message, welcome_text)
298|
299|
300|@bot.message_handler(func=lambda message: True)
301|def handle_team_search(message: Message):
302|    """Handle team search queries"""
303|    team_name = message.text.strip()
304|    
305|    if len(team_name) < 2:
306|        bot.reply_to(message, "⚠️ Пожалуйста, введите более длинное название команды.")
307|        return
308|    
309|    # Send "searching" message
310|    searching_msg = bot.reply_to(message, f"🔍 Ищу матчи для команды '{team_name}'...")
311|    
312|    try:
313|        # Search for team and matches
314|        match_data = search_team_matches(team_name)
315|        
316|        if not match_data:
317|            bot.edit_message_text(
318|                f"❌ Команда '{team_name}' не найдена.\n\nПопробуйте написать название на английском (например: Barcelona, Chelsea, Bayern).",
319|                chat_id=message.chat.id,
320|                message_id=searching_msg.message_id
321|            )
322|            return
323|        
324|        match = match_data.get("match")
325|        
326|        if match:
327|            # Get AI prediction
328|            home_team = match.get("homeTeam", {}).get("name", "Home")
329|            away_team = match.get("awayTeam", {}).get("name", "Away")
330|            competition = match.get("competition", {}).get("name", "Tournament")
331|            
332|            bot.edit_message_text(
333|                f"✅ Нашёл матч! Генерирую прогноз...",
334|                chat_id=message.chat.id,
335|                message_id=searching_msg.message_id
336|            )
337|            
338|            # Run async prediction in event loop
339|            loop = asyncio.new_event_loop()
340|            asyncio.set_event_loop(loop)
341|            try:
342|                prediction = loop.run_until_complete(get_ai_prediction(home_team, away_team, competition))
343|            finally:
344|                loop.close()
345|        else:
346|            prediction = None
347|        
348|        # Format and send response
349|        response = format_match_message(match_data, prediction)
350|        
351|        bot.edit_message_text(
352|            response,
353|            chat_id=message.chat.id,
354|            message_id=searching_msg.message_id
355|        )
356|        
357|    except Exception as e:
358|        logger.error(f"Error handling team search: {e}")
359|        bot.edit_message_text(
360|            "❌ Произошла ошибка при поиске. Попробуйте ещё раз позже.",
361|            chat_id=message.chat.id,
362|            message_id=searching_msg.message_id
363|        )
364|
365|
366|def run_bot():
367|    """Run the bot with polling"""
368|    logger.info("Starting Telegram bot...")
369|    try:
370|        bot.infinity_polling(timeout=60, long_polling_timeout=60)
371|    except Exception as e:
372|        logger.error(f"Bot polling error: {e}")
373|        raise
374|
375|
376|if __name__ == "__main__":
377|    run_bot()
378|
