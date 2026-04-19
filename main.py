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

WEEKDAYS_UZ = {
    "Monday": "Dushanba", "Tuesday": "Seshanba", "Wednesday": "Chorshanba",
    "Thursday": "Payshanba", "Friday": "Juma", "Saturday": "Shanba", "Sunday": "Yakshanba"
}

# --- RASM YARATISH FUNKSIYASI (ULKAN YOZUVLI) ---
def create_image(title, text, footer):
    width, height = 1200, 1200
    img = Image.new('RGB', (width, height), color='#1e293b') # To'q ko'k/kulrang fon
    draw = ImageDraw.Draw(img)
    
    try:
        f_title = ImageFont.truetype("arial.ttf", 80)
        f_text = ImageFont.truetype("arial.ttf", 65)
        f_footer = ImageFont.truetype("arial.ttf", 45)
    except:
        f_title = ImageFont.load_default(); f_text = ImageFont.load_default(); f_footer = ImageFont.load_default()

    # Sarlavha
    draw.text((width/2, 150), title, fill="#38bdf8", font=f_title, anchor="mm")
    
    # Matnni qatorlarga bo'lish (Avtomatik wrapping)
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        if len(" ".join(current_line)) > 30:
            lines.append(" ".join(current_line))
            current_line = []
    lines.append(" ".join(current_line))
    
    # Matnni markazga yozish
    y_text = 400
    for line in lines:
        draw.text((width/2, y_text), line, fill="#ffffff", font=f_text, anchor="mm")
        y_text += 90

    # Pastki qism
    draw.text((width/2, height-100), footer, fill="#94a3b8", font=f_footer, anchor="mm")
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

# --- VAZIFALAR ---

def job_morning(): # 05:30
    now = datetime.now(tashkent_tz)
    weekday = WEEKDAYS_UZ.get(now.strftime('%A'), now.strftime('%A'))
    try:
        r = requests.get(f"http://api.aladhan.com/v1/gToH?date={now.strftime('%d-%m-%Y')}").json()
        h = r['data']['hijri']
        hijri_txt = f"{h['day']} {h['month']['en']} {h['year']}-yil"
    except: hijri_txt = "Barakali kun"

    tilaklar = [
        "Bugungi kuningiz mo'jizalarga boy bo'lsin! ✨",
        "Yangi kunni tabassum bilan boshlang! 🌟",
        "Siz bugun har qachongidan ham kuchlisiz! 💪"
    ]
    
    msg = (f"☀️ **XAYRLI TONG!**\n\n📅 {now.strftime('%Y-%m-%d')}\n"
           f"🌙 {hijri_txt}\n🗓 {weekday}\n\n"
           f"✨ {random.choice(tilaklar)}\n\n@karnayuzb")
    bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")

def job_fact_image(): # 07:00
    try:
        r = requests.get("https://uselessfacts.jsph.pl/random.json?language=en").json()
        uz_text = translator.translate(r['text'], dest='uz').text
        photo = create_image("QIZIQARLI FAKT", uz_text, "@karnayuzb")
        bot.send_photo(CHANNEL_ID, photo, caption="💡 Kunlik qiziqarli fakt!")
    except: pass

def job_motivation_image(): # 09:00
    try:
        r = requests.get("https://api.quotable.io/random?tags=wisdom|success").json()
        uz_quote = translator.translate(f"{r['content']} — {r['author']}", dest='uz').text
        photo = create_image("KUN MOTIVATSIYASI", uz_quote, "@karnayuzb")
        bot.send_photo(CHANNEL_ID, photo, caption="🚀 Ruhiy quvvat va motivatsiya!")
    except: pass

def job_quiz(): # 12:00, 15:00, 18:00
    try:
        r = requests.get("https://opentdb.com/api.php?amount=1&type=multiple").json()['results'][0]
        q = translator.translate(r['question'], dest='uz').text
        c = translator.translate(r['correct_answer'], dest='uz').text
        opts = [translator.translate(o, dest='uz').text for o in r['incorrect_answers']] + [c]
        random.shuffle(opts)
        bot.send_poll(CHANNEL_ID, f"🤔 VIKTORINA: {q}", opts, type='quiz', correct_option_id=opts.index(c), is_anonymous=False)
    except: pass

# --- SERVER VA SCHEDULER ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is running!", 200

scheduler = BackgroundScheduler(timezone=tashkent_tz)
scheduler.add_job(job_morning, 'cron', hour=5, minute=30)
scheduler.add_job(job_fact_image, 'cron', hour=7, minute=0)
scheduler.add_job(job_motivation_image, 'cron', hour=9, minute=0)
for h in [12, 15, 18]: scheduler.add_job(job_quiz, 'cron', hour=h, minute=0)
scheduler.start()

if __name__ == "__main__":
    Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))).start()
    bot.infinity_polling(timeout=60)
