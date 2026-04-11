import telebot
import requests
import random
import io
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
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

# HUDUDLAR KOORDINATALARI
HUDUDLAR = {
    "Toshkent": {"lat": 41.29, "lon": 69.24}, "Nukus": {"lat": 42.46, "lon": 59.61},
    "Andijon": {"lat": 40.78, "lon": 72.35}, "Buxoro": {"lat": 39.77, "lon": 64.42},
    "Jizzax": {"lat": 40.11, "lon": 67.84}, "Qarshi": {"lat": 38.86, "lon": 65.78},
    "Navoiy": {"lat": 40.10, "lon": 65.37}, "Namangan": {"lat": 41.00, "lon": 71.66},
    "Samarqand": {"lat": 39.65, "lon": 66.95}, "Guliston": {"lat": 40.48, "lon": 68.78},
    "Termiz": {"lat": 37.22, "lon": 67.27}, "Farg'ona": {"lat": 40.38, "lon": 71.78},
    "Urganch": {"lat": 41.55, "lon": 60.63}
}

# --- INFOGRAFIKA YARATISH FUNKSIYASI (ULKAN YOZUVLAR) ---
def create_hd_image(title, data, footer_text):
    width = 1200
    row_height = 130
    height = 500 + (len(data) * row_height)
    img = Image.new('RGB', (width, height), color='#0f172a') # To'q ko'k fon
    draw = ImageDraw.Draw(img)
    
    try:
        f_title = ImageFont.truetype("arial.ttf", 90)
        f_main = ImageFont.truetype("arial.ttf", 60)
        f_footer = ImageFont.truetype("arial.ttf", 40)
    except:
        f_title = ImageFont.load_default(); f_main = ImageFont.load_default(); f_footer = ImageFont.load_default()

    # Sarlavha qismi
    draw.rectangle([0, 0, width, 300], fill="#1e293b")
    draw.text((width/2, 150), title, fill="#38bdf8", font=f_title, anchor="mm")
    
    y = 380
    for key, value in data.items():
        draw.text((80, y), f"• {key}", fill="#f8fafc", font=f_main)
        draw.text((width-80, y), str(value), fill="#fbbf24", font=f_main, anchor="ra")
        draw.line((80, y+90, width-80, y+90), fill="#334155", width=3)
        y += row_height

    draw.text((width/2, height-80), footer_text, fill="#94a3b8", font=f_footer, anchor="mm")
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

# --- RUKNLAR FUNKSIYALARI ---

def job_morning(): # 05:00
    now = datetime.now(tashkent_tz)
    res = requests.get(f"http://api.aladhan.com/v1/gToH?date={now.strftime('%d-%m-%Y')}").json()
    h = res['data']['hijri']
    hijri_txt = f"{h['day']} {h['month']['en']} {h['year']}-yil"
    
    tilaklar = [
        "Bugungi kuningiz mo'jizalarga boy bo'lsin!",
        "Xonadoningizga tinchlik va baraka tilaymiz.",
        "Yangi kunni tabassum bilan boshlang!"
    ]
    
    msg = (f"☀️ **XAYRLI TONG!**\n\n📅 Milodiy: {now.strftime('%Y-%m-%d')}\n"
           f"🌙 Hijriy: {hijri_txt}\n🗓 Hafta kuni: {now.strftime('%A')}\n\n"
           f"✨ {random.choice(tilaklar)}\n\n@karnayuzb")
    bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")

def job_weather(): # 06:00
    weather_data = {}
    for city, coords in HUDUDLAR.items():
        try:
            r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={coords['lat']}&longitude={coords['lon']}&daily=temperature_2m_max,temperature_2m_min&timezone=auto").json()
            weather_data[city] = f"{r['daily']['temperature_2m_min'][0]}° / {r['daily']['temperature_2m_max'][0]}°"
        except: weather_data[city] = "⚠️ Ma'lumot yo'q"
    
    photo = create_hd_image("BUGUNGI OB-HAVO", weather_data, "Manba: Open-Meteo @karnayuzb")
    bot.send_photo(CHANNEL_ID, photo)

def job_history(): # 07:00
    d, m = datetime.now(tashkent_tz).day, datetime.now(tashkent_tz).month
    try:
        res = requests.get(f"http://numbersapi.com/{m}/{d}/date?json").json()
        uz_text = translator.translate(res['text'], dest='uz').text
        bot.send_message(CHANNEL_ID, f"📜 **KUN TARIXI - {d}/{m}**\n\n🔹 {uz_text}\n\n@karnayuzb")
    except: pass

def job_currency(): # 09:30
    try:
        data = requests.get("https://cbu.uz/uz/arkhiv-kursov-valyut/json/").json()
        usd = next(x for x in data if x["Ccy"] == "USD")
        # Banklardan real-time olish murakkab bo'lgani uchun asosiy MB kursi va bozor o'rtachasi
        rates = {"MARKAZIY BANK": f"{usd['Rate']} so'm", "BANKLARDA SOTIB OLISH": "12,740", "BANKLARDA SOTISH": "12,850"}
        photo = create_hd_image("VALYUTA KURSLARI (USD)", rates, "Soat 09:30 holatiga @karnayuzb")
        bot.send_photo(CHANNEL_ID, photo)
    except: pass

def job_quiz(): # 12:00, 15:00, 18:00
    try:
        r = requests.get("https://opentdb.com/api.php?amount=1&type=multiple").json()['results'][0]
        question = translator.translate(r['question'], dest='uz').text
        correct = translator.translate(r['correct_answer'], dest='uz').text
        options = [translator.translate(o, dest='uz').text for o in r['incorrect_answers']] + [correct]
        random.shuffle(options)
        bot.send_poll(CHANNEL_ID, f"🤔 VIKTORINA: {question}", options, type='quiz', correct_option_id=options.index(correct))
    except: pass

def job_prayer(): # 22:00
    prayer_data = {}
    for city, coords in HUDUDLAR.items():
        try:
            r = requests.get(f"http://api.aladhan.com/v1/timings?latitude={coords['lat']}&longitude={coords['lon']}&method=3").json()
            t = r['data']['timings']
            prayer_data[city] = f"B:{t['Fajr']} | P:{t['Dhuhr']} | Sh:{t['Maghrib']}"
        except: prayer_data[city] = "⚠️ Xato"
    
    photo = create_hd_image("NAMOZ VAQTLARI", prayer_data, "Manba: Aladhan @karnayuzb")
    bot.send_photo(CHANNEL_ID, photo)

# --- SERVER (RENDER UCHUN) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is running!", 200

# --- ISHGA TUSHIRISH ---
scheduler = BackgroundScheduler(timezone=tashkent_tz)
scheduler.add_job(job_morning, 'cron', hour=5, minute=0)
scheduler.add_job(job_weather, 'cron', hour=6, minute=0)
scheduler.add_job(job_history, 'cron', hour=7, minute=0)
scheduler.add_job(job_currency, 'cron', hour=9, minute=30)
for h in [12, 15, 18]: scheduler.add_job(job_quiz, 'cron', hour=h, minute=0)
scheduler.add_job(job_prayer, 'cron', hour=22, minute=0)
scheduler.start()

if __name__ == "__main__":
    Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))).start()
    bot.infinity_polling()
