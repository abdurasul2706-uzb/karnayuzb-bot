import telebot
import requests
import random
import io
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from apscheduler.schedulers.background import BackgroundWorker
import pytz
from googletrans import Translator

# --- SOZLAMALAR ---
TOKEN = "8222976736:AAEHmKeTga27Fq2YnUlK4ld1x0DVtWdb5gs"
CHANNEL_ID = "@karnayuzb"
bot = telebot.TeleBot(TOKEN)
translator = Translator()
tashkent_tz = pytz.timezone('Asia/Tashkent')

HUDUDLAR = {
    "Toshkent": {"lat": 41.29, "lon": 69.24}, "Nukus": {"lat": 42.46, "lon": 59.61},
    "Andijon": {"lat": 40.78, "lon": 72.35}, "Buxoro": {"lat": 39.77, "lon": 64.42},
    "Jizzax": {"lat": 40.11, "lon": 67.84}, "Qarshi": {"lat": 38.86, "lon": 65.78},
    "Navoiy": {"lat": 40.10, "lon": 65.37}, "Namangan": {"lat": 41.00, "lon": 71.66},
    "Samarqand": {"lat": 39.65, "lon": 66.95}, "Guliston": {"lat": 40.48, "lon": 68.78},
    "Termiz": {"lat": 37.22, "lon": 67.27}, "Farg'ona": {"lat": 40.38, "lon": 71.78},
    "Urganch": {"lat": 41.55, "lon": 60.63}
}

# --- INFOGRAFIKA (O'TA KATTA YOZUVLAR) ---
def create_image(title, data, footer):
    width = 1200
    row_h = 130
    height = 500 + (len(data) * row_h)
    img = Image.new('RGB', (width, height), color='#0f172a')
    draw = ImageDraw.Draw(img)
    
    try:
        f_title = ImageFont.truetype("arial.ttf", 90)
        f_main = ImageFont.truetype("arial.ttf", 65) # Yirik yozuv
        f_footer = ImageFont.truetype("arial.ttf", 45)
    except:
        f_title = ImageFont.load_default(); f_main = ImageFont.load_default(); f_footer = ImageFont.load_default()

    draw.rectangle([0, 0, width, 300], fill="#1e293b")
    draw.text((width/2, 150), title, fill="#38bdf8", font=f_title, anchor="mm")
    
    y = 380
    for k, v in data.items():
        draw.text((80, y), f"• {k}", fill="#f8fafc", font=f_main)
        draw.text((width-80, y), str(v), fill="#fbbf24", font=f_main, anchor="ra")
        draw.line((80, y+95, width-80, y+95), fill="#334155", width=4)
        y += row_h

    draw.text((width/2, height-80), footer, fill="#94a3b8", font=f_footer, anchor="mm")
    buf = io.BytesIO(); img.save(buf, format='PNG'); buf.seek(0)
    return buf

# --- VAZIFALAR ---
def job_morning():
    now = datetime.now(tashkent_tz)
    res = requests.get(f"http://api.aladhan.com/v1/gToH?date={now.strftime('%d-%m-%Y')}").json()
    h = res['data']['hijri']
    msg = (f"☀️ **XAYRLI TONG!**\n\n📅 {now.strftime('%Y-%m-%d')}\n🌙 Hijriy: {h['day']} {h['month']['en']}\n"
           f"✨ Bugungi kuningiz barakali o'tsin! @karnayuzb")
    bot.send_message(CHANNEL_ID, msg)

def job_weather():
    res = {}
    for c, coord in HUDUDLAR.items():
        try:
            r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={coord['lat']}&longitude={coord['lon']}&daily=temperature_2m_max,temperature_2m_min&timezone=auto").json()
            res[c] = f"{r['daily']['temperature_2m_min'][0]}° / {r['daily']['temperature_2m_max'][0]}°"
        except: res[c] = "⚠️ Ma'lumot yo'q"
    photo = create_image("BUGUNGI OB-HAVO", res, "Manba: Meteo @karnayuzb")
    bot.send_photo(CHANNEL_ID, photo)

def job_history():
    d, m = datetime.now(tashkent_tz).day, datetime.now(tashkent_tz).month
    try:
        r = requests.get(f"http://numbersapi.com/{m}/{d}/date?json").json()
        uz = translator.translate(r['text'], dest='uz').text
        bot.send_message(CHANNEL_ID, f"📜 **KUN TARIXI**\n\n🔹 {uz}\n\n@karnayuzb")
    except: pass

def job_currency():
    try:
        data = requests.get("https://cbu.uz/uz/arkhiv-kursov-valyut/json/").json()
        usd = next(x for x in data if x["Ccy"] == "USD")
        rates = {"MARKAZIY BANK": f"{usd['Rate']} so'm", "BANKLARDA SOTIB OLISH": "12,740", "BANKLARDA SOTISH": "12,850"}
        photo = create_image("VALYUTA KURSLARI", rates, "Soat 09:30 holatiga")
        bot.send_photo(CHANNEL_ID, photo)
    except: pass

def job_quiz():
    try:
        r = requests.get("https://opentdb.com/api.php?amount=1&type=multiple").json()['results'][0]
        q = translator.translate(r['question'], dest='uz').text
        c = translator.translate(r['correct_answer'], dest='uz').text
        opts = [translator.translate(o, dest='uz').text for o in r['incorrect_answers']] + [c]
        random.shuffle(opts)
        bot.send_poll(CHANNEL_ID, f"🤔 VIKTORINA: {q}", opts, type='quiz', correct_option_id=opts.index(c))
    except: pass

def job_prayer():
    res = {}
    for c, coord in HUDUDLAR.items():
        try:
            r = requests.get(f"http://api.aladhan.com/v1/timings?latitude={coord['lat']}&longitude={coord['lon']}&method=3").json()
            t = r['data']['timings']
            res[c] = f"B:{t['Fajr']} | P:{t['Dhuhr']} | Sh:{t['Maghrib']}"
        except: res[c] = "⚠️ Xato"
    photo = create_image("NAMOZ VAQTLARI", res, "@karnayuzb")
    bot.send_photo(CHANNEL_ID, photo)

# --- SERVER VA SCHEDULER ---
from flask import Flask
server = Flask(__name__)
@server.route("/")
def webhook(): return "Bot is alive", 200

scheduler = BackgroundWorker(timezone=tashkent_tz)
scheduler.add_job(job_morning, 'cron', hour=5, minute=0)
scheduler.add_job(job_weather, 'cron', hour=6, minute=0)
scheduler.add_job(job_history, 'cron', hour=7, minute=0)
scheduler.add_job(job_currency, 'cron', hour=9, minute=30)
for h in [12, 15, 18]: scheduler.add_job(job_quiz, 'cron', hour=h, minute=0)
scheduler.add_job(job_prayer, 'cron', hour=22, minute=0)
scheduler.start()

if __name__ == "__main__":
    # Render uchun port
    port = int(os.environ.get("PORT", 5000))
    from threading import Thread
    Thread(target=lambda: server.run(host="0.0.0.0", port=port)).start()
    bot.remove_webhook()
    bot.infinity_polling(timeout=60)
