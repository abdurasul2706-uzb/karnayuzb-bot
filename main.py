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
from aiohttp import web

# --- SOZLAMALAR ---
TOKEN = "8222976736:AAEHmKeTga27Fq2YnUlK4ld1x0DVtWdb5gs"
CHANNEL_ID = "@karnayuzb"

bot = Bot(token=TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
translator = Translator()

# HUDUDLAR KOORDINATALARI
HUDUDLAR = {
    "Toshkent": {"lat": 41.29, "lon": 69.24}, "Andijon": {"lat": 40.78, "lon": 72.35},
    "Buxoro": {"lat": 39.77, "lon": 64.42}, "Guliston": {"lat": 40.48, "lon": 68.78},
    "Jizzax": {"lat": 40.11, "lon": 67.84}, "Navoiy": {"lat": 40.10, "lon": 65.37},
    "Namangan": {"lat": 41.00, "lon": 71.66}, "Nukus": {"lat": 42.46, "lon": 59.61},
    "Samarqand": {"lat": 39.65, "lon": 66.95}, "Termiz": {"lat": 37.22, "lon": 67.27},
    "Farg'ona": {"lat": 40.38, "lon": 71.78}, "Urganch": {"lat": 41.55, "lon": 60.63},
    "Qarshi": {"lat": 38.86, "lon": 65.78}
}

# --- INFOGRAFIKA (Dinamik va Kengaytirilgan) ---
def create_infographic(title, data, footer, theme="#0f172a"):
    # Namoz vaqtlari sig'ishi uchun rasm kengligini 1200 px qildim
    height = 500 + (len(data) * 115)
    img = Image.new('RGB', (1200, height), color=theme)
    draw = ImageDraw.Draw(img)
    try:
        f_title = ImageFont.truetype("arial.ttf", 75)
        f_main = ImageFont.truetype("arial.ttf", 38)
    except:
        f_title = ImageFont.load_default(); f_main = ImageFont.load_default()

    draw.rectangle([0, 0, 1200, 250], fill="#1e293b")
    draw.text((600, 125), title, fill="#38bdf8", font=f_title, anchor="mm")
    
    y = 320
    for k, v in data.items():
        draw.text((50, y), f"• {k}", fill="#f8fafc", font=f_main)
        draw.text((1150, y), str(v), fill="#fbbf24", font=f_main, anchor="ra")
        draw.line((50, y+80, 1150, y+80), fill="#334155", width=2)
        y += 120

    draw.text((600, height-80), footer, fill="#94a3b8", font=f_main, anchor="mm")
    buf = io.BytesIO(); img.save(buf, format='PNG'); buf.seek(0)
    return buf

# --- AVTOMATIK RUKNLAR ---

# 1. 05:00 - Xayrli tong
async def job_morning():
    try:
        res = requests.get(f"http://api.aladhan.com/v1/gToH?date={datetime.now().strftime('%d-%m-%Y')}").json()
        h = res['data']['hijri']
        hijri = f"{h['day']} {h['month']['en']} {h['year']}-yil"
        weekdays = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]
        text = (f"☀️ **XAYRLI TONG, @karnayuzb!**\n\n📅 Bugun: {datetime.now().strftime('%Y-%m-%d')}\n"
                f"🌙 Hijriy: {hijri}\n🗓 Kun: {weekdays[datetime.now().weekday()]}\n\n"
                f"✨ Boshlagan kuningiz hayrli va barakali o'tsin!")
        await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown")
    except: pass

# 2. 06:00 - Ob-havo
async def job_weather():
    weather_results = {}
    for city, c in HUDUDLAR.items():
        try:
            w = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={c['lat']}&longitude={c['lon']}&daily=temperature_2m_max,temperature_2m_min&timezone=auto").json()
            weather_results[city] = f"Min: {w['daily']['temperature_2m_min'][0]}° / Max: {w['daily']['temperature_2m_max'][0]}° ☀️"
        except: weather_results[city] = "⚠️ Ma'lumot olinmadi"
    photo = create_infographic("BUGUNGI OB-HAVO", weather_results, "Manba: Open-Meteo | @karnayuzb")
    await bot.send_photo(CHANNEL_ID, photo=BufferedInputFile(photo.read(), filename="w.png"))

# 3. 07:00 - Tarixda bugun
async def job_history():
    try:
        soup = BeautifulSoup(requests.get("https://uz.wikipedia.org/wiki/Portal:Bugun").text, 'lxml')
        events = [li.text for li in soup.find_all('li')[:8] if len(li.text) > 40]
        await bot.send_message(CHANNEL_ID, "📜 **TARIXDA BUGUN:**\n\n" + "\n\n".join(events))
    except: pass

# 4. 09:30 - Valyuta kurslari (Barcha banklar)
async def job_currency():
    bank_data = {}
    try:
        soup = BeautifulSoup(requests.get("https://banklar.uz/uz/currency/usd").text, 'lxml')
        rows = soup.find('table').find_all('tr')[1:]
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 3:
                bank_data[cols[0].text.strip()] = f"{cols[1].text.strip()} / {cols[2].text.strip()}"
    except: bank_data["XATOLIK"] = "⚠️ Banklar ro'yxati yangilanmadi"
    photo = create_infographic("VALYUTA: BANKLAR USD KURSI", bank_data, "9:30 dagi real kurslar")
    await bot.send_photo(CHANNEL_ID, photo=BufferedInputFile(photo.read(), filename="c.png"))

# 5. Viktorina (12:00, 15:00, 18:00)
async def job_quiz():
    try:
        q = requests.get("https://opentdb.com/api.php?amount=1&type=multiple").json()['results'][0]
        question = translator.translate(q['question'], dest='uz').text
        options = [translator.translate(o, dest='uz').text for o in q['incorrect_answers']]
        correct = translator.translate(q['correct_answer'], dest='uz').text
        options.append(correct); random.shuffle(options)
        await bot.send_poll(CHANNEL_ID, question, options, is_anonymous=False, type='quiz', correct_option_id=options.index(correct))
    except: pass

# 6. 22:00 - 5 Mahal Namoz vaqtlari
async def job_prayer():
    prayer_results = {}
    for city, c in HUDUDLAR.items():
        try:
            p = requests.get(f"http://api.aladhan.com/v1/timings?latitude={c['lat']}&longitude={c['lon']}&method=3").json()
            t = p['data']['timings']
            # Bomdod, Quyosh, Peshin, Asr, Shom, Xufton
            prayer_results[city] = f"B:{t['Fajr']} | Q:{t['Sunrise']} | P:{t['Dhuhr']} | A:{t['Asr']} | Sh:{t['Maghrib']} | X:{t['Isha']}"
        except: prayer_results[city] = "⚠️ Aniqlab bo'lmadi"
    photo = create_infographic("5 MAHAL NAMOZ VAQTLARI (ERTAGA)", prayer_results, "Manba: Aladhan MWL | @karnayuzb", theme="#064e3b")
    await bot.send_photo(CHANNEL_ID, photo=BufferedInputFile(photo.read(), filename="p.png"), caption="🕌 Ertangi kun uchun namoz taqvimi.")

# --- CRON-JOB UCHUN UYG'OTUVCHI ---
async def handle_ping(request):
    return web.Response(text="Bot tirik!", status=200)

# --- ASOSIY ISHGA TUSHIRISH (VAQTLAR SHU YERDA) ---
async def main():
    # Vaqtlarni rejalashtirish (Siz aytganidek)
    scheduler.add_job(job_morning, 'cron', hour=5, minute=0)   # 05:00
    scheduler.add_job(job_weather, 'cron', hour=6, minute=0)   # 06:00
    scheduler.add_job(job_history, 'cron', hour=7, minute=0)   # 07:00
    scheduler.add_job(job_currency, 'cron', hour=9, minute=30) # 09:30
    
    # Viktorinalar 3 marta
    scheduler.add_job(job_quiz, 'cron', hour=12, minute=0)
    scheduler.add_job(job_quiz, 'cron', hour=15, minute=0)
    scheduler.add_job(job_quiz, 'cron', hour=18, minute=0)
    
    scheduler.add_job(job_prayer, 'cron', hour=22, minute=0)   # 22:00
    
    scheduler.start()

    # Veb-server (Cron-job uchun)
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    await site.start()

    logging.info("Bot tayyor va vaqtlar sozlandi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
