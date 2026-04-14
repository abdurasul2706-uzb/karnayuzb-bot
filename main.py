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

# --- VAZIFALAR ---

def job_morning(): # 05:00 - Xayrli tong va Hijriy sana
    now = datetime.now(tashkent_tz)
    weekday_uz = WEEKDAYS_UZ.get(now.strftime('%A'), now.strftime('%A'))
    
    # Hijriy sanani olish (Zaxira bilan)
    try:
        r = requests.get(f"http://api.aladhan.com/v1/gToH?date={now.strftime('%d-%m-%Y')}", timeout=10).json()
        h = r['data']['hijri']
        hijri_txt = f"{h['day']} {h['month']['en']} {h['year']}-yil"
    except:
        hijri_txt = "Barakali kun"

    tilaklar = [
        "Bugun shunday kun bo'lsinki, hatto eng kichik orzuingiz ham ushalsin! ✨",
        "Yangi kunni tabassum bilan boshlang, u sizga baxt ulashsin! 🌟",
        "Siz bugun har qachongidan ham kuchlisiz, ishlaringizda zafarlar tilaymiz! 💪",
        "Ertalabki rejalaringiz barakali, kuningiz esa quvonchli o'tsin! 😊"
    ]
    
    msg = (f"☀️ **XAYRLI TONG, AZIZ OBUNACHI!**\n\n"
           f"📅 Milodiy: {now.strftime('%Y-%m-%d')}\n"
           f"🌙 Hijriy: {hijri_txt}\n"
           f"🗓 Hafta kuni: {weekday_uz}\n\n"
           f"✨ {random.choice(tilaklar)}\n\n@karnayuzb")
    bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")

def job_facts(): # 07:00 - Cheksiz Qiziqarli Faktlar
    try:
        # Dunyo bo'ylab tasodifiy faktlar bazasidan olish
        r = requests.get("https://uselessfacts.jsph.pl/random.json?language=en", timeout=10).json()
        uz_fact = translator.translate(r['text'], dest='uz').text
        bot.send_message(CHANNEL_ID, f"💡 **BILASIZMI?**\n\n{uz_fact}\n\n@karnayuzb")
    except:
        # Zaxira fakt
        bot.send_message(CHANNEL_ID, "💡 **BILASIZMI?**\n\nInson miyasi kunduzidagidan ko'ra tunda faolroq ishlaydi.\n\n@karnayuzb")

def job_motivation(): # 09:30 - Cheksiz Motivatsiya
    try:
        # Mashhur iqtiboslar bazasidan olish
        r = requests.get("https://api.quotable.io/random?tags=wisdom|success", timeout=10).json()
        en_text = f"{r['content']} — {r['author']}"
        uz_quote = translator.translate(en_text, dest='uz').text
        bot.send_message(CHANNEL_ID, f"🚀 **KUN MOTIVATSIYASI**\n\n{uz_quote}\n\n@karnayuzb")
    except:
        bot.send_message(CHANNEL_ID, "🚀 **KUN MOTIVATSIYASI**\n\nKichik qadamlar buyuk natijalarga olib keladi. To'xtamang!\n\n@karnayuzb")

def job_quiz(): # 12:00, 15:00, 18:00 - Cheksiz Viktorinalar
    try:
        # Open Trivia DB bazasidan tasodifiy savol olish
        r = requests.get("https://opentdb.com/api.php?amount=1&type=multiple", timeout=10).json()['results'][0]
        
        q = translator.translate(r['question'], dest='uz').text
        c = translator.translate(r['correct_answer'], dest='uz').text
        opts = [translator.translate(o, dest='uz').text for o in r['incorrect_answers']] + [c]
        
        # JAVOBLARNI ARALASHTIRISH (Har doim har xil o'rinda chiqadi)
        random.shuffle(opts)
        correct_id = opts.index(c)
        
        bot.send_poll(
            CHANNEL_ID, 
            f"🤔 VIKTORINA: {q}", 
            opts, 
            type='quiz', 
            correct_option_id=correct_id, 
            is_anonymous=False
        )
    except:
        print("Viktorina yuborishda xatolik yuz berdi.")

# --- SERVER (RENDER UCHUN) ---
app = Flask(__name__)
@app.route("/")
def health(): return "Karnayuzb Bot Is Alive", 200

# --- SCHEDULER (VAQTNI SOZLASH) ---
scheduler = BackgroundScheduler(timezone=tashkent_tz)

scheduler.add_job(job_morning, 'cron', hour=5, minute=0)
scheduler.add_job(job_facts, 'cron', hour=7, minute=0)
scheduler.add_job(job_motivation, 'cron', hour=9, minute=30)

# Kuniga 3 marta viktorina
for h in [12, 15, 18]:
    scheduler.add_job(job_quiz, 'cron', hour=h, minute=0)

scheduler.start()

if __name__ == "__main__":
    # Render portini sozlash
    port = int(os.environ.get("PORT", 5000))
    Thread(target=lambda: app.run(host="0.0.0.0", port=port)).start()
    
    # Botni ishga tushirish (Polling)
    bot.infinity_polling(timeout=60, long_polling_timeout=5)
