import asyncio
import json
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
db = {
    "blacklist": [],
    "clients": {},
    "bookings": {}
}
TOKEN = "8763057998:AAFQsPbthBy9PUVIdsI47wFx49sfnsn_WZo"
ADMIN_ID = 809778427

bot = Bot(token=TOKEN)
dp = Dispatcher()

FILE = "crm.json"

if os.path.exists(FILE):
    with open(FILE, "r") as f:
        db = json.load(f)

    # 💥 гарантуємо що всі ключі є
    if "blacklist" not in db:
        db["blacklist"] = []
    if "clients" not in db:
        db["clients"] = {}
    if "bookings" not in db:
        db["bookings"] = {}
    if "blocked_dates" not in db:
        db["blocked_dates"] = []

else:
    db = {
        "bookings": {},
        "clients": {},
        "blacklist": [],
        "blocked_dates": []
    }
    

def save():
    with open(FILE, "w") as f:
        json.dump(db, f, indent=4)

users = {}

WORK_START = 10
WORK_END = 18

def to_min(t):
    h, m = map(int, t.split(":"))
    return h*60+m

def to_time(m):
    return f"{m//60:02d}:{m%60:02d}"

def weekends():
    now = datetime.now()
    res = []
    for i in range(14):
        d = now + timedelta(days=i)
        if d.weekday() in [5,6]:
            date = d.strftime("%d.%m")
            if date not in db["blocked_dates"]:
                res.append(date)
    return res[:4]
@dp.message(Command("list"))
async def list_bookings(m: Message):
    if not db["bookings"]:
        await m.answer("❌ Записів поки немає")
        return

    text = "📋 Всі записи:\n\n"

for date, items in db["bookings"].items():
    text += f"📅 {date}\n"
    
    for b in items:
        text += f"  🕐 {b['time']} — {b['name']} ({b['phone']})\n"
    
    text += "\n"

await message.answer(text)

  
def free_slots(date, duration):
    duration = int(duration.split()[0])
    day = db["bookings"].get(date, [])

    res = []
    start = WORK_START*60
    end = WORK_END*60

    while start+duration <= end:
        ok = True
        for b in day:
            s = to_min(b["time"])
            e = s + b["duration"]
            if not (start+duration <= s or start >= e):
                ok = False
        if ok:
            res.append(to_time(start))
        start += 30
    return res

# --- KEYBOARDS ---
main_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Записатися")]],
    resize_keyboard=True
)

client_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Скасувати запис")],
        [KeyboardButton(text="Перенести запис")]
    ],
    resize_keyboard=True
)

# --- START ---
@dp.message(Command("start"))
async def start(m: Message):
    if "blacklist" in db and m.from_user.id in db["blacklist"]:
        return
    await m.answer("Вітаю!Майстер Тетяна,рада Вам допомогти 💆‍♀️", reply_markup=main_kb)

# --- CANCEL ---
@dp.message(lambda m: m.text == "Скасувати запис")
async def cancel(m: Message):
    phone = None
    for cl in db["clients"]:
        if db["clients"][cl]["name"]:
            pass

    for d in db["bookings"]:
        db["bookings"][d] = [
            b for b in db["bookings"][d]
            if b["phone"] != m.text
        ]

    save()
    await m.answer("Скасовано ❌")

# --- TRANSFER START ---
@dp.message(lambda m: m.text == "Перенести запис")
async def transfer(m: Message):
    users[m.from_user.id] = {"transfer": True}
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=d)] for d in weekends()],
        resize_keyboard=True
    )
    await m.answer("Оберіть нову дату", reply_markup=kb)

# --- HANDLE ---
@dp.message()
async def h(m: Message):
    uid = m.from_user.id
    text = m.text

    if uid in db["blacklist"]:
        return

    # --- TRANSFER FLOW ---
    if uid in users and users[uid].get("transfer"):
        if "date" not in users[uid]:
            users[uid]["date"] = text
            slots = free_slots(text, "60 хв")
            kb = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=s)] for s in slots],
                resize_keyboard=True
            )
            await m.answer("Новий час", reply_markup=kb)
            return

        elif "time" not in users[uid]:
            new_time = text

            # знайти старий запис
            for d in db["bookings"]:
                for b in db["bookings"][d]:
                    if b["phone"] == str(uid):
                        db["bookings"][d].remove(b)

            # додати новий
            db["bookings"].setdefault(users[uid]["date"], []).append({
                "time": new_time,
                "duration": 60,
                "price": 1000,
                "name": "перенесено",
                "phone": str(uid)
            })
            
            save()
            users.pop(uid)

            await m.answer("Перенесено ✅", reply_markup=client_kb)
            return

    # --- NEW BOOKING ---
    if text == "Записатися":
        users[uid] = {}
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Спина")],
                [KeyboardButton(text="Задня поверхня")],
                [KeyboardButton(text="Комбінований")],
                [KeyboardButton(text="Тайський")],
                [KeyboardButton(text="Іспанський")]
            ],
            resize_keyboard=True
        )
        await m.answer("Масаж", reply_markup=kb)

    elif uid in users and "type" not in users[uid]:
        users[uid]["type"] = text

        if text == "Задня поверхня":
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="40 хв")]
                ],
                resize_keyboard=True
            )
        else:
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="30 хв")],
                    [KeyboardButton(text="60 хв")],
                    [KeyboardButton(text="90 хв")]
                ],
                resize_keyboard=True
            )

        await m.answer("Тривалість", reply_markup=kb)

    elif uid in users and "duration" not in users[uid]:
        users[uid]["duration"] = text

        prices = {"30 хв":500,"40 хв":600,"60 хв":1000,"90 хв":1500}
        users[uid]["price"] = prices.get(text,0)

        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=d)] for d in weekends()],
            resize_keyboard=True
        )
        await m.answer("Дата", reply_markup=kb)

    elif uid in users and "date" not in users[uid]:
        users[uid]["date"] = text

        slots = free_slots(text, users[uid]["duration"])

        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=s)] for s in slots],
            resize_keyboard=True
        )
        await m.answer("Час", reply_markup=kb)

    elif uid in users and "time" not in users[uid]:
        users[uid]["time"] = text
        await m.answer("Ім'я", reply_markup=ReplyKeyboardRemove())

    elif uid in users and "name" not in users[uid]:
        users[uid]["name"] = text
        await m.answer("Телефон")

    elif uid in users and "phone" not in users[uid]:
        users[uid]["phone"] = text
        d = users[uid]

        bookings = db["bookings"].setdefault(d["date"], [])
    
        # перевірка чи час зайнятий
        for b in bookings:
            if b["time"] == d["time"]:
                await m.answer("❌ Цей час вже зайнятий")
                return
        
     # якщо вільно — додаємо
    bookings.append({
    "time": d["time"],
    "duration": int(d["duration"].split()[0]),
    "price": d["price"],
    "name": d["name"],
    "phone": d["phone"]
    })
    
     from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
db["clients"][str(m.from_user.id)] = d
save()

kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="❌ Скасувати", callback_data=f"cancel_{d['date']}"),
        InlineKeyboardButton(text="🔄 Перенести", callback_data=f"move_{d['date']}")
    ]
])

await bot.send_message(
    ADMIN_ID,
    f"✨ НОВИЙ ЗАПИС:\n\n"
    f"👤 {d['name']}\n"
    f"📞 {d['phone']}\n"
    f"📅 {d['date']}\n"
    f"🕒 {d['time']}",
    reply_markup=kb
)
        await m.answer(text)
        users.pop(user_id)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
