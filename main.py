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

# --- SOZLAMALAR ---
TOKEN = "8222976736:AAEHmKeTga27Fq2YnUlK4ld1x0DVtWdb5gs"
CHANNEL_ID = "@karnayuzb"

bot = Bot(token=TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
translator = Translator()

HUDUDLAR = {
    "Toshkent": {"lat": 41.29, "lon": 69.24}, "Andijon": {"lat": 40.78, "lon": 72.35},
    "Buxoro": {"lat": 39.77, "lon": 64.42}, "Guliston": {"lat": 40.48, "lon": 68.78},
    "Jizzax": {"lat": 40.11, "lon": 67.84}, "Zarafshon": {"lat": 41.57, "lon": 64.19},
    "Karmana": {"lat": 40.13, "lon": 65.35}, "Namangan": {"lat": 41.00, "lon": 71.66},
    "Nukus": {"lat": 42.46, "lon": 59.61}, "Samarqand": {"lat": 39.65, "lon": 66.95},
    "Termiz": {"lat": 37.22, "lon": 67.27}, "Urganch": {"lat": 41.55, "lon": 60.63},
    "Farg'ona": {"lat": 40.38, "lon": 71.78}, "Qarshi": {"lat": 38.86, "lon": 65.78}
}

# --- INFOGRAFIKA GENERATORI (XATO VA ALDOVSIZ) ---
def create_infographic(title, data, footer, theme="#0f172a"):
    height = 500 + (len(data) * 110)
    img = Image.new('RGB', (1080, height), color=theme)
    draw = ImageDraw.Draw(img)
    try:
        f_title = ImageFont.truetype("arial.ttf", 80)
        f_main = ImageFont.truetype("arial.ttf", 45)
    except:
        f_title = ImageFont.load_default(); f_main = ImageFont.load_default()

    draw.rectangle([0, 0, 1080, 250], fill="#1e293b")
    draw.text((540, 125), title, fill="#38bdf8", font=f_title, anchor="mm")
    
    y = 320
    for k, v in data.items():
        draw.text((80, y), f"• {k}", fill="#f8fafc", font=f_main)
        # Agar ma'lumot kelmasa, qizil rangda ogohlantirish beradi
        val_color = "#fbbf24" if "Xatolik" not in str(v) else "#f43f5e"
        draw.text((1000, y), str(v), fill=val_color, font=f_main, anchor="ra")
        draw.line((80, y+75, 1000, y+75), fill="#334155", width=2)
        y += 115

    draw.text((540, height-80), footer, fill="#94a3b8", font=f_main, anchor="mm")
    buf = io.BytesIO(); img.save(buf, format='PNG'); buf.seek(0)
    return buf

# --- RUKNLAR ---

# 1. Xayrli tong (05:00)
async def job_morning():
    try:
        res = requests.get(f"http://api.aladhan.com/v1/gToH?date={datetime.now().strftime('%d-%m-%Y')}").json()
        h = res['data']['hijri']
        hijri = f"{h['day']} {h['month']['en']} {h['year']}-yil"
        weekdays = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]
        text = (f"☀️ **XAYRLI TONG, @karnayuzb!**\n\n📅 Milodiy: {datetime.now().strftime('%Y-%m-%d')}\n"
                f"🌙 Hijriy: {hijri}\n🗓 Kun: {weekdays[datetime.now().weekday()]}\n\n"
                f"✨ Bugungi kuningiz barakali o'tsin!")
        await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown")
    except Exception as e: logging.error(f"Tong xatosi: {e}")

# 2. Ob-havo (06:00) - REAL API
async def job_weather():
    weather_results = {}
    for city, c in HUDUDLAR.items():
        try:
            w = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={c['lat']}&longitude={c['lon']}&daily=temperature_2m_max,temperature_2m_min&timezone=auto").json()
            weather_results[city] = f"{w['daily']['temperature_2m_min'][0]}° / {w['daily']['temperature_2m_max'][0]}° ⛅"
        except: weather_results[city] = "⚠️ Xatolik"
    
    photo = create_infographic("BUGUNGI OB-HAVO", weather_results, "Faqat ishonchli manbalardan")
    await bot.send_photo(CHANNEL_ID, photo=BufferedInputFile(photo.read(), filename="w.png"))

# 3. Kun tarixi (07:00)
async def job_history():
    try:
        soup = BeautifulSoup(requests.get("https://uz.wikipedia.org/wiki/Portal:Bugun").text, 'lxml')
        events = [li.text for li in soup.find_all('li')[:8] if len(li.text) > 40]
        await bot.send_message(CHANNEL_ID, "📜 **TARIXDA BUGUN:**\n\n" + "\n\n".join(events))
    except: pass

# 4. VALYUTA (09:30) - BARCHA BANKLAR (SCRAPING)
async def job_currency():
    bank_data = {}
    try:
        # Haqiqiy va barcha banklar uchun agregator saytdan skaner qilish
        soup = BeautifulSoup(requests.get("https://banklar.uz/uz/currency/usd").text, 'lxml')
        rows = soup.find('table').find_all('tr')[1:]
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 3:
                bank_data[cols[0].text.strip()] = f"{cols[1].text.strip()} / {cols[2].text.strip()}"
    except: bank_data["TIZIM"] = "⚠️ Ma'lumot olishda xatolik"

    photo = create_infographic("BARCHA BANKLAR USD KURSI", bank_data, "9:30 dagi real holat")
    await bot.send_photo(CHANNEL_ID, photo=BufferedInputFile(photo.read(), filename="c.png"))

# 5. VIKTORINALAR (Cheksiz API)
async def job_quiz():
    try:
        q_data = requests.get("https://opentdb.com/api.php?amount=1&type=multiple").json()['results'][0]
        question = translator.translate(q_data['question'], dest='uz').text
        options = [translator.translate(o, dest='uz').text for o in q_data['incorrect_answers']]
        correct = translator.translate(q_data['correct_answer'], dest='uz').text
        options.append(correct); random.shuffle(options)
        await bot.send_poll(CHANNEL_ID, question, options, is_anonymous=False, type='quiz', correct_option_id=options.index(correct))
    except: pass

# 6. NAMOZ VAQTLARI (22:00)
async def job_prayer():
    prayer_results = {}
    for city, c in HUDUDLAR.items():
        try:
            p = requests.get(f"http://api.aladhan.com/v1/timings?latitude={c['lat']}&longitude={c['lon']}&method=3").json()
            t = p['data']['timings']
            prayer_results[city] = f"B: {t['Fajr']} | Sh: {t['Maghrib']}"
        except: prayer_results[city] = "⚠️ Xatolik"
    
    photo = create_infographic("NAMOZ VAQTLARI (ERTAGA)", prayer_results, "Islomiy manbalar asosida", theme="#064e3b")
    await bot.send_photo(CHANNEL_ID, photo=BufferedInputFile(photo.read(), filename="p.png"))

# --- ASOSIY ISHGA TUSHIRISH ---
async def main():
    scheduler.add_job(job_morning, 'cron', hour=5, minute=0)
    scheduler.add_job(job_weather, 'cron', hour=6, minute=0)
    scheduler.add_job(job_history, 'cron', hour=7, minute=0)
    scheduler.add_job(job_currency, 'cron', hour=9, minute=30)
    for h in [12, 15, 18]: scheduler.add_job(job_quiz, 'cron', hour=h, minute=0)
    scheduler.add_job(job_prayer, 'cron', hour=22, minute=0)
    
    scheduler.start()
    logging.info("Bot tayyor!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
