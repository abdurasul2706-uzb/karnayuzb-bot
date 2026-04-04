import asyncio
import logging
import requests
import random
import io
import re
from datetime import datetime
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from aiogram import Bot, Dispatcher, types
from aiogram.types import BufferedInputFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from googletrans import Translator
from aiohttp import web

# --- ASOSIY SOZLAMALAR ---
TOKEN = "8222976736:AAEHmKeTga27Fq2YnUlK4ld1x0DVtWdb5gs"
CHANNEL_ID = "@karnayuzb"

bot = Bot(token=TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
translator = Translator()

# HUDUDLAR KOORDINATALARI (Ob-havo va Namoz uchun)
HUDUDLAR = {
    "TOSHKENT": {"lat": 41.29, "lon": 69.24}, "NUKUS": {"lat": 42.46, "lon": 59.61},
    "ANDIJON": {"lat": 40.78, "lon": 72.35}, "BUXORO": {"lat": 39.77, "lon": 64.42},
    "GULISTON": {"lat": 40.48, "lon": 68.78}, "JIZZAX": {"lat": 40.11, "lon": 67.84},
    "NAVOIY": {"lat": 40.10, "lon": 65.37}, "NAMANGAN": {"lat": 41.00, "lon": 71.66},
    "SAMARQAND": {"lat": 39.65, "lon": 66.95}, "TERMIZ": {"lat": 37.22, "lon": 67.27},
    "FARG'ONA": {"lat": 40.38, "lon": 71.78}, "URGANCH": {"lat": 41.55, "lon": 60.63},
    "QARSHI": {"lat": 38.86, "lon": 65.78}
}

# --- MEGA INFOGRAFIKA GENERATORI (Yozuvlar 300% kattalashtirilgan) ---
def create_mega_infographic(title, data, footer, theme="#0f172a"):
    width = 1300 # Rasm kengligini oshirdik
    row_h = 140  # Har bir qator balandligi
    height = 600 + (len(data) * row_h)
    img = Image.new('RGB', (width, height), color=theme)
    draw = ImageDraw.Draw(img)
    
    try:
        # Render.com da shrift bo'lmasa xato bermasligi uchun load_default bor
        f_title = ImageFont.truetype("arial.ttf", 100)
        f_main = ImageFont.truetype("arial.ttf", 65) # JUDA KATTA YOZUV
        f_footer = ImageFont.truetype("arial.ttf", 50)
    except:
        f_title = ImageFont.load_default(); f_main = ImageFont.load_default(); f_footer = ImageFont.load_default()

    # Sarlavha foni
    draw.rectangle([0, 0, width, 320], fill="#1e293b")
    draw.text((width/2, 160), title, fill="#38bdf8", font=f_title, anchor="mm")
    
    y = 400
    for key, val in data.items():
        draw.text((80, y), f"• {key}", fill="#f8fafc", font=f_main)
        draw.text((width-80, y), str(val), fill="#fbbf24", font=f_main, anchor="ra")
        draw.line((80, y+100, width-80, y+100), fill="#334155", width=5)
        y += row_h

    draw.text((width/2, height-100), footer, fill="#94a3b8", font=f_footer, anchor="mm")
    buf = io.BytesIO(); img.save(buf, format='PNG'); buf.seek(0)
    return buf

# --- RUKNLAR FUNKSIYASI ---

async def job_morning():
    try:
        res = requests.get(f"http://api.aladhan.com/v1/gToH?date={datetime.now().strftime('%d-%m-%Y')}").json()
        h = res['data']['hijri']
        hijri = f"{h['day']} {h['month']['en']} {h['year']}-yil"
        weekdays = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]
        tilaklar = [
            "Assalomu alaykum! Bugungi kuningiz mo'jizalarga boy bo'lsin. Har bir qadamingizda omad, har bir nafasingizda baxt hamroh bo'lsin!",
            "Xayrli tong! Sizga sihat-salomatlik, oilaviy xotirjamlik va bitmas-tuganmas baraka tilaymiz. Kuningiz samarali o'tsin!",
            "G'animat tong muborak! Qalbingiz nurga, xonadoningiz fayzga to'lsin. Ezgu niyatlaringiz ijobat bo'lishini tilaymiz!"
        ]
        msg = (f"☀️ **XAYRLI TONG, QADRLI OBUNACHI!**\n\n📅 **Milodiy:** {datetime.now().strftime('%Y-%m-%d')}\n"
               f"🌙 **Hijriy:** {hijri}\n🗓 **Kun:** {weekdays[datetime.now().weekday()]}\n\n✨ {random.choice(tilaklar)}\n\n@karnayuzb")
        await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
    except: pass

async def job_weather():
    w_res = {}
    for city, c in HUDUDLAR.items():
        for _ in range(3):
            try:
                r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={c['lat']}&longitude={c['lon']}&daily=temperature_2m_max,temperature_2m_min&timezone=auto", timeout=10).json()
                w_res[city] = f"{r['daily']['temperature_2m_min'][0]}° / {r['daily']['temperature_2m_max'][0]}° 🌤"
                break
            except: await asyncio.sleep(2)
        if city not in w_res: w_res[city] = "⚠️ ALOQA YO'Q"
    
    photo = create_mega_infographic("BUGUNGI OB-HAVO", w_res, "Manba: METEO-CENTER | @karnayuzb")
    await bot.send_photo(CHANNEL_ID, BufferedInputFile(photo.read(), "w.png"))

async def job_history():
    try:
        # NumbersAPI va Wikipedia orqali tarixiy fakt
        d, m = datetime.now().day, datetime.now().month
        res = requests.get(f"http://numbersapi.com/{m}/{d}/date", timeout=10).text
        uz_text = translator.translate(res, dest='uz').text
        await bot.send_message(CHANNEL_ID, f"📜 **KUN TARIXI - {d}/{m}**\n\n🔹 {uz_text}\n\n@karnayuzb")
    except: pass

async def job_currency():
    rates = {}
    try:
        # Banklar.uz skanerlash
        soup = BeautifulSoup(requests.get("https://banklar.uz/uz/currency/usd", timeout=15).text, 'lxml')
        table_rows = soup.find_all('tr')[1:12] # Top 11 ta bank
        for row in table_rows:
            cols = row.find_all('td')
            if len(cols) >= 3:
                name = cols[0].get_text(strip=True)[:15].upper()
                rates[name] = f"S: {cols[1].get_text(strip=True)} / O: {cols[2].get_text(strip=True)}"
    except: rates["MARKAZIY BANK"] = "12,750 so'm (Yangilanmoqda)"
    
    photo = create_mega_infographic("BANKLAR USD KURSI", rates, "S: Sotib olish | O: Sotish | @karnayuzb")
    await bot.send_photo(CHANNEL_ID, BufferedInputFile(photo.read(), "c.png"))

async def job_quiz():
    try:
        # Cheksiz savollar bazasi
        r = requests.get("https://opentdb.com/api.php?amount=1&type=multiple").json()['results'][0]
        q = translator.translate(r['question'], dest='uz').text
        correct = translator.translate(r['correct_answer'], dest='uz').text
        options = [translator.translate(o, dest='uz').text for o in r['incorrect_answers']]
        options.append(correct); random.shuffle(options)
        await bot.send_poll(CHANNEL_ID, f"🤔 VIKTORINA: {q}", options, type='quiz', correct_option_id=options.index(correct), is_anonymous=False)
    except: pass

async def job_prayer():
    p_res = {}
    for city, c in HUDUDLAR.items():
        try:
            r = requests.get(f"http://api.aladhan.com/v1/timings?latitude={c['lat']}&longitude={c['lon']}&method=3").json()
            t = r['data']['timings']
            p_res[city] = f"B:{t['Fajr']} | P:{t['Dhuhr']} | A:{t['Asr']} | Sh:{t['Maghrib']} | X:{t['Isha']}"
        except: p_res[city] = "⚠️ Olinmadi"
    
    photo = create_mega_infographic("NAMOZ VAQTLARI (ERTAGA)", p_res, "Manba: ISLOM.UZ / Aladhan", theme="#064e3b")
    await bot.send_photo(CHANNEL_ID, BufferedInputFile(photo.read(), "p.png"))

# --- SERVER VA SCHEDULER ---
async def handle_ping(r): return web.Response(text="OK")

async def main():
    scheduler.add_job(job_morning, 'cron', hour=5, minute=0)
    scheduler.add_job(job_weather, 'cron', hour=6, minute=0)
    scheduler.add_job(job_history, 'cron', hour=7, minute=0)
    scheduler.add_job(job_currency, 'cron', hour=9, minute=30)
    for h in [12, 15, 18]: scheduler.add_job(job_quiz, 'cron', hour=h, minute=0)
    scheduler.add_job(job_prayer, 'cron', hour=22, minute=0)
    scheduler.start()

    app = web.Application(); app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', 10000).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
