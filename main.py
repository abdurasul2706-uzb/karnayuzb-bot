import telebot
import requests
import random
import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
from googletrans import Translator
from flask import Flask
from threading import Thread

# --- KONFIGURATSIYA ---
TOKEN = "8222976736:AAEHmKeTga27Fq2YnUlK4ld1x0DVtWdb5gs"
CHANNEL_ID = "@karnayuzb"
bot = telebot.TeleBot(TOKEN)
translator = Translator()
tashkent_tz = pytz.timezone('Asia/Tashkent')

WEEKDAYS_UZ = {
    "Monday": "Dushanba", "Tuesday": "Seshanba", "Wednesday": "Chorshanba",
    "Thursday": "Payshanba", "Friday": "Juma", "Saturday": "Shanba", "Sunday": "Yakshanba"
}

HUDUDLAR = {
    "Toshkent": {"lat": 41.29, "lon": 69.24}, "Nukus": {"lat": 42.46, "lon": 59.61},
    "Andijon": {"lat": 40.78, "lon": 72.35}, "Buxoro": {"lat": 39.77, "lon": 64.42},
    "Jizzax": {"lat": 40.11, "lon": 67.84}, "Qarshi": {"lat": 38.86, "lon": 65.78},
    "Navoiy": {"lat": 40.10, "lon": 65.37}, "Namangan": {"lat": 41.00, "lon": 71.66},
    "Samarqand": {"lat": 39.65, "lon": 66.95}, "Guliston": {"lat": 40.48, "lon": 68.78},
    "Termiz": {"lat": 37.22, "lon": 67.27}, "Farg'ona": {"lat": 40.38, "lon": 71.78},
    "Urganch": {"lat": 41.55, "lon": 60.63}
}

# --- VAZIFALAR ---

def job_morning(): # 05:00 - Xayrli tong
    now = datetime.now(tashkent_tz)
    weekday_uz = WEEKDAYS_UZ.get(now.strftime('%A'), now.strftime('%A'))
    try:
        r = requests.get(f"http://api.aladhan.com/v1/gToH?date={now.strftime('%d-%m-%Y')}").json()
        h = r['data']['hijri']
        hijri_txt = f"{h['day']} {h['month']['en']} {h['year']}-yil"
    except: hijri_txt = "Barakali kun"

    tilaklar = [
        "Bugun shunday kun bo'lsinki, hatto eng kichik orzuingiz ham ushalsin! ✨",
        "Ertalabki rejalaringiz barakali, kuningiz esa quvonchli o'tsin! 🌟",
        "Siz bugun har qachongidan ham kuchlisiz, ishlaringizda zafarlar tilaymiz! 💪"
    ]
    
    msg = (f"☀️ **XAYRLI TONG, AZIZ OBUNACHI!**\n\n"
           f"📅 Milodiy: {now.strftime('%Y-%m-%d')}\n"
           f"🌙 Hijriy: {hijri_txt}\n"
           f"🗓 Hafta kuni: {weekday_uz}\n\n"
           f"✨ {random.choice(tilaklar)}\n\n@karnayuzb")
    bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")

def job_weather(): # 06:00 - Ob-havo (Hamma viloyatlar)
    text = "🌤 **BUGUNGI OB-HAVO MA'LUMOTLARI**\n\n"
    for city, coord in HUDUDLAR.items():
        try:
            r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={coord['lat']}&longitude={coord['lon']}&daily=temperature_2m_max,temperature_2m_min&timezone=auto").json()
            t_min = r['daily']['temperature_2m_min'][0]
            t_max = r['daily']['temperature_2m_max'][0]
            text += f"📍 {city}: {t_min}° / {t_max}°\n"
        except: text += f"📍 {city}: Ma'lumot aniqlanmoqda...\n"
    
    text += "\n@karnayuzb"
    bot.send_message(CHANNEL_ID, text, parse_mode="Markdown")

def job_facts(): # 07:00 - Cheksiz Faktlar
    try:
        res = requests.get("https://uselessfacts.jsph.pl/random.json?language=en").json()
        uz_fact = translator.translate(res['text'], dest='uz').text
        bot.send_message(CHANNEL_ID, f"💡 **BILASIZMI?**\n\n{uz_fact}\n\n@karnayuzb")
    except: pass

def job_motivation(): # 09:30 - Cheksiz Motivatsiya
    try:
        res = requests.get("https://api.quotable.io/random?tags=wisdom|success").json()
        uz_quote = translator.translate(f"{res['content']} — {res['author']}", dest='uz').text
        bot.send_message(CHANNEL_ID, f"🚀 **KUN MOTIVATSIYASI**\n\n{uz_quote}\n\n@karnayuzb")
    except: pass

def job_quiz(): # 12:00, 15:00, 18:00 - Cheksiz Viktorina
    try:
        r = requests.get("https://opentdb.com/api.php?amount=1&type=multiple").json()['results'][0]
        q = translator.translate(r['question'], dest='uz').text
        c = translator.translate(r['correct_answer'], dest='uz').text
        opts = [translator.translate(o, dest='uz').text for o in r['incorrect_answers']] + [c]
        random.shuffle(opts)
        bot.send_poll(CHANNEL_ID, f"🤔 VIKTORINA: {q}", opts, type='quiz', correct_option_id=opts.index(c), is_anonymous=False)
    except: pass

# --- SERVER ---
app = Flask(__name__)
@app.route("/")
def home(): return "Bot Is Running", 200

# --- ISHGA TUSHIRISH ---
scheduler = BackgroundScheduler(timezone=tashkent_tz)
scheduler.add_job(job_morning, 'cron', hour=5, minute=0)
scheduler.add_job(job_weather, 'cron', hour=6, minute=0)
scheduler.add_job(job_facts, 'cron', hour=7, minute=0)
scheduler.add_job(job_motivation, 'cron', hour=9, minute=30)
for h in [12, 15, 18]: scheduler.add_job(job_quiz, 'cron', hour=h, minute=0)
scheduler.start()

if __name__ == "__main__":
    Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))).start()
    bot.infinity_polling(timeout=60)
