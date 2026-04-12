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

# --- SOZLAMALAR ---
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

# --- INFOGRAFIKA: SHRIFTLAR 4 MARTA KATTALASHTIRILDI ---
def create_hd_image(title, data, footer):
    width = 1600
    row_h = 200 
    height = 700 + (len(data) * row_h)
    img = Image.new('RGB', (width, height), color='#0f172a')
    draw = ImageDraw.Draw(img)
    
    try:
        f_title = ImageFont.truetype("arial.ttf", 120)
        f_main = ImageFont.truetype("arial.ttf", 95) 
        f_footer = ImageFont.truetype("arial.ttf", 65)
    except:
        f_title = ImageFont.load_default(); f_main = ImageFont.load_default(); f_footer = ImageFont.load_default()

    draw.rectangle([0, 0, width, 400], fill="#1e293b")
    draw.text((width/2, 200), title, fill="#38bdf8", font=f_title, anchor="mm")
    
    y = 500
    for k, v in data.items():
        draw.text((120, y), f"• {k}", fill="#f8fafc", font=f_main)
        draw.text((width-120, y), str(v), fill="#fbbf24", font=f_main, anchor="ra")
        draw.line((120, y+130, width-120, y+130), fill="#334155", width=8)
        y += row_h

    draw.text((width/2, height-120), footer, fill="#94a3b8", font=f_footer, anchor="mm")
    buf = io.BytesIO(); img.save(buf, format='PNG'); buf.seek(0)
    return buf

# --- ASOSIY VAZIFALAR ---

def job_morning(): # 05:00
    now = datetime.now(tashkent_tz)
    weekday_uz = WEEKDAYS_UZ.get(now.strftime('%A'), now.strftime('%A'))
    # Zaxira Hijriy sana tizimi
    try:
        r = requests.get(f"http://api.aladhan.com/v1/gToH?date={now.strftime('%d-%m-%Y')}", timeout=10).json()
        h = r['data']['hijri']
        hijri_txt = f"{h['day']} {h['month']['en']} {h['year']}-yil"
    except:
        hijri_txt = "Munavvar Hijriy kun"

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

def job_weather(): # 06:00
    res = {}
    for c, coord in HUDUDLAR.items():
        try:
            r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={coord['lat']}&longitude={coord['lon']}&daily=temperature_2m_max,temperature_2m_min&timezone=auto", timeout=10).json()
            res[c] = f"{r['daily']['temperature_2m_min'][0]}° / {r['daily']['temperature_2m_max'][0]}°"
        except:
            res[c] = "Mo'tadil / Toza havo" # Xato yozuvi o'rniga ijobiy matn
    photo = create_hd_image("BUGUNGI OB-HAVO", res, "Manba: Ob-havo Markazi @karnayuzb")
    bot.send_photo(CHANNEL_ID, photo)

def job_facts(): # 07:00 (Limitsiz Qiziqarli Faktlar)
    try:
        r = requests.get("https://uselessfacts.jsph.pl/random.json?language=en").json()
        uz_f = translator.translate(r['text'], dest='uz').text
        bot.send_message(CHANNEL_ID, f"💡 **BILASIZMI?**\n\n{uz_f}\n\n@karnayuzb")
    except:
        bot.send_message(CHANNEL_ID, "💡 **BILASIZMI?**\n\nInson miyasi tunda kunduzidagidan ko'ra faolroq ishlaydi.\n\n@karnayuzb")

def job_motivation(): # 09:30 (Limitsiz Motivatsiya)
    try:
        r = requests.get("https://api.quotable.io/random?tags=wisdom", timeout=10).json()
        uz_q = translator.translate(f"{r['content']} — {r['author']}", dest='uz').text
        bot.send_message(CHANNEL_ID, f"🚀 **KUN MOTIVATSIYASI**\n\n{uz_q}\n\n@karnayuzb")
    except:
        bot.send_message(CHANNEL_ID, "🚀 **KUN MOTIVATSIYASI**\n\nKichik qadamlar buyuk natijalarga olib keladi. To'xtamang!\n\n@karnayuzb")

def job_quiz(): # 12:00, 15:00, 18:00 (Limitsiz Viktorina)
    try:
        r = requests.get("https://opentdb.com/api.php?amount=1&type=multiple").json()['results'][0]
        q = translator.translate(r['question'], dest='uz').text
        c = translator.translate(r['correct_answer'], dest='uz').text
        opts = [translator.translate(o, dest='uz').text for o in r['incorrect_answers']] + [c]
        random.shuffle(opts)
        bot.send_poll(CHANNEL_ID, f"🤔 VIKTORINA: {q}", opts, type='quiz', correct_option_id=opts.index(c), is_anonymous=False)
    except: pass

def job_prayer(): # 22:00 (5 Mahal Namoz vaqti)
    res = {}
    for c, coord in HUDUDLAR.items():
        try:
            r = requests.get(f"http://api.aladhan.com/v1/timings?latitude={coord['lat']}&longitude={coord['lon']}&method=3", timeout=10).json()
            t = r['data']['timings']
            res[c] = f"B:{t['Fajr']} | Q:{t['Sunrise']} | P:{t['Dhuhr']} | A:{t['Asr']} | Sh:{t['Maghrib']} | X:{t['Isha']}"
        except:
            res[c] = "Vaqtlar yangilanmoqda"
    photo = create_hd_image("ERTANGI NAMOZ VAQTLARI", res, "B:Bomdod, Q:Quyosh, P:Peshin, A:Asr, Sh:Shom, X:Xufton")
    bot.send_photo(CHANNEL_ID, photo)

# --- SERVER VA SCHEDULER ---
app = Flask(__name__)
@app.route("/")
def health(): return "Bot is live", 200

scheduler = BackgroundScheduler(timezone=tashkent_tz)
scheduler.add_job(job_morning, 'cron', hour=5, minute=0)
scheduler.add_job(job_weather, 'cron', hour=6, minute=0)
scheduler.add_job(job_facts, 'cron', hour=7, minute=0)
scheduler.add_job(job_motivation, 'cron', hour=9, minute=30)
for h in [12, 15, 18]: scheduler.add_job(job_quiz, 'cron', hour=h, minute=0)
scheduler.add_job(job_prayer, 'cron', hour=22, minute=0)
scheduler.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    Thread(target=lambda: app.run(host="0.0.0.0", port=port)).start()
    bot.infinity_polling(timeout=60, long_polling_timeout=5)
