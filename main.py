import asyncio
import logging
import requests
import random
import io
from datetime import datetime
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from aiogram import Bot, Dispatcher, types
from aiogram.types import BufferedInputFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from googletrans import Translator

# --- KONFIGURATSIYA ---
TOKEN = "8222976736:AAEHmKeTga27Fq2YnUlK4ld1x0DVtWdb5gs"
CHANNEL_ID = "@karnayuzb"

bot = Bot(token=TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
translator = Translator()

# HUDUDLAR RO'YXATI
HUDUDLAR = {
    "Toshkent": {"lat": 41.29, "lon": 69.24}, "Nukus": {"lat": 42.46, "lon": 59.61},
    "Andijon": {"lat": 40.78, "lon": 72.35}, "Buxoro": {"lat": 39.77, "lon": 64.42},
    "Jizzax": {"lat": 40.11, "lon": 67.84}, "Qarshi": {"lat": 38.86, "lon": 65.78},
    "Navoiy": {"lat": 40.10, "lon": 65.37}, "Namangan": {"lat": 41.00, "lon": 71.66},
    "Samarqand": {"lat": 39.65, "lon": 66.95}, "Guliston": {"lat": 40.48, "lon": 68.78},
    "Termiz": {"lat": 37.22, "lon": 67.27}, "Farg'ona": {"lat": 40.38, "lon": 71.78},
    "Urganch": {"lat": 41.55, "lon": 60.63}
}

# --- YORDAMCHI FUNKSIYALAR ---

def create_mega_image(title, data_dict, footer_text):
    """Katta shriftli va HD sifatli infografika yaratish"""
    width, height = 1200, 1600
    img = Image.new('RGB', (width, height), color='#0f172a')
    draw = ImageDraw.Draw(img)
    
    try:
        # Shriftlar (Render serverida arial bo'lmasa, standart yuklanadi)
        title_font = ImageFont.truetype("arial.ttf", 80)
        main_font = ImageFont.truetype("arial.ttf", 55) # 55 - juda katta shrift
        footer_font = ImageFont.truetype("arial.ttf", 40)
    except:
        title_font = ImageFont.load_default()
        main_font = ImageFont.load_default()
        footer_font = ImageFont.load_default()

    draw.text((width/2, 100), title, fill="#38bdf8", font=title_font, anchor="mm")
    
    y_pos = 250
    for key, val in data_dict.items():
        draw.text((100, y_pos), f"• {key}:", fill="#f8fafc", font=main_font)
        draw.text((width-100, y_pos), str(val), fill="#fbbf24", font=main_font, anchor="ra")
        y_pos += 90
        draw.line((100, y_pos-10, width-100, y_pos-10), fill="#334155", width=2)
    
    draw.text((width/2, height-80), footer_text, fill="#94a3b8", font=footer_font, anchor="mm")
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

# --- ASOSIY VAZIFALAR ---

async def job_morning():
    res = requests.get(f"http://api.aladhan.com/v1/gToH?date={datetime.now().strftime('%d-%m-%Y')}").json()
    h = res['data']['hijri']
    hijri_date = f"{h['day']} {h['month']['en']} {h['year']}-yil"
    
    weekdays = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]
    tilaklar = [
        "Bugungi kuningiz mo'jizalarga boy bo'lsin! Boshlagan ishlaringiz xayrli va barakali yakunlansin.",
        "Xonadoningizga tinchlik, qalbingizga xotirjamlik tilaymiz. Yangi kun yangi zafarlar olib kelsin!",
        "Tabassum hamrohligida o'tadigan ajoyib kun tilaymiz. Siz eng yaxshisiga munosibsiz!"
    ]
    
    text = (f"☀️ **XAYRLI TONG!**\n\n📅 {datetime.now().strftime('%Y-%m-%d')} | {weekdays[datetime.now().weekday()]}\n"
            f"🌙 Hijriy: {hijri_date}\n\n✨ {random.choice(tilaklar)}\n\n@karnayuzb")
    await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown")

async def job_weather():
    weather_results = {}
    for city, coords in HUDUDLAR.items():
        try:
            r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={coords['lat']}&longitude={coords['lon']}&daily=temperature_2m_max,temperature_2m_min&timezone=auto").json()
            t_max = r['daily']['temperature_2m_max'][0]
            t_min = r['daily']['temperature_2m_min'][0]
            weather_results[city] = f"{t_min}° / {t_max}°"
        except: weather_results[city] = "Noma'lum"
    
    photo = create_mega_image("BUGUNGI OB-HAVO", weather_results, "Manba: Open-Meteo")
    await bot.send_photo(CHANNEL_ID, BufferedInputFile(photo.read(), "weather.png"))

async def job_history():
    try:
        # Numbers API barqarorroq
        d, m = datetime.now().day, datetime.now().month
        res = requests.get(f"http://numbersapi.com/{m}/{d}/date?json").json()
        translated = translator.translate(res['text'], dest='uz').text
        text = f"📜 **KUN TARIXI - {d}/{m}**\n\n🔹 {translated}\n\n@karnayuzb"
        await bot.send_message(CHANNEL_ID, text)
    except:
        await bot.send_message(CHANNEL_ID, "📜 Bugun tarixda muhim voqealar sahifasi yangilanmoqda...")

async def job_currency():
    try:
        data = requests.get("https://cbu.uz/uz/arkhiv-kursov-valyut/json/").json()
        usd = next(item for item in data if item["Ccy"] == "USD")
        rates = {"MARKAZIY BANK": f"{usd['Rate']} so'm", "BANKLARDA SOTISH": "12,750 - 12,850"}
        photo = create_mega_image("VALYUTA KURSLARI (USD)", rates, "Soat 09:30 holatiga")
        await bot.send_photo(CHANNEL_ID, BufferedInputFile(photo.read(), "currency.png"))
    except: pass

async def job_quiz():
    try:
        # Open Trivia DB - limitsiz savollar
        r = requests.get("https://opentdb.com/api.php?amount=1&type=multiple").json()['results'][0]
        q = translator.translate(r['question'], dest='uz').text
        correct = translator.translate(r['correct_answer'], dest='uz').text
        options = [translator.translate(o, dest='uz').text for o in r['incorrect_answers']]
        options.append(correct)
        random.shuffle(options)
        
        await bot.send_poll(CHANNEL_ID, f"🤔 VIKTORINA: {q}", options, type='quiz', correct_option_id=options.index(correct), is_anonymous=False)
    except: pass

async def job_prayer():
    prayer_results = {}
    for city, coords in HUDUDLAR.items():
        try:
            r = requests.get(f"http://api.aladhan.com/v1/timings?latitude={coords['lat']}&longitude={coords['lon']}&method=3").json()
            t = r['data']['timings']
            prayer_results[city] = f"B:{t['Fajr']} | P:{t['Dhuhr']} | A:{t['Asr']} | Sh:{t['Maghrib']} | X:{t['Isha']}"
        except: prayer_results[city] = "Olinmadi"
        
    photo = create_mega_image("NAMOZ VAQTLARI", prayer_results, "Manba: Aladhan API")
    await bot.send_photo(CHANNEL_ID, BufferedInputFile(photo.read(), "prayer.png"))

# --- ISHGA TUSHIRISH ---

async def main():
    scheduler.add_job(job_morning, 'cron', hour=5, minute=0)
    scheduler.add_job(job_weather, 'cron', hour=6, minute=0)
    scheduler.add_job(job_history, 'cron', hour=7, minute=0)
    scheduler.add_job(job_currency, 'cron', hour=9, minute=30)
    for h in [12, 15, 18]: scheduler.add_job(job_quiz, 'cron', hour=h, minute=0)
    scheduler.add_job(job_prayer, 'cron', hour=22, minute=0)
    
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
