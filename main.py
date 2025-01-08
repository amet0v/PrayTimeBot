import asyncio
# import datetime
import logging
from datetime import datetime, timedelta

import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)
# Объект бота
bot = Bot(token="7643270300:AAFzD_AYudYe7vCpzQhPko5YFsnd8w1JiG8")
# Диспетчер
dp = Dispatcher()

scheduler_main = AsyncIOScheduler(timezone=timezone("Asia/Bishkek"))
scheduler = AsyncIOScheduler(timezone=timezone("Asia/Bishkek"))


class TimeHolder:
    time_schedule = "empty string"


async def get_time():
    date = datetime.now().strftime("%d-%m-%Y")
    url = f"http://api.aladhan.com/v1/timingsByCity/{date}?city=Bishkek&country=KGZ&school=1"
    resp = requests.get(url)
    data = resp.json()
    time_array = [data["data"]["timings"]["Fajr"],
                  data["data"]["timings"]["Dhuhr"],
                  data["data"]["timings"]["Asr"],
                  data["data"]["timings"]["Maghrib"],
                  data["data"]["timings"]["Isha"]]
    return time_array


async def send_time():
    #msg = \
    await bot.send_message(chat_id="-1001860566817", text=TimeHolder.time_schedule)
    #await bot.pin_chat_message("-1001860566817", msg.message_id)


async def round_time(time_str):
    time_obj = datetime.strptime(time_str, "%H:%M")
    minutes = (time_obj.minute + 4) // 5 * 5
    if minutes >= 60:
        time_obj += timedelta(hours=1)
        minutes = 0
    rounded_time = time_obj.replace(minute=minutes, second=0, microsecond=0)
    adjusted_time = rounded_time - timedelta(minutes=15)
    return [rounded_time.hour, rounded_time.minute,
            adjusted_time.hour, adjusted_time.minute]  # pray: 0 - h 1 - m; notify: 2 - h 3 - m;


async def send_notification(h, m):
    today = datetime.now().weekday()
    if today != 5 and today != 6:
        await bot.send_message("-1001860566817", f"🛐 Намаз в {h}:{m}")


async def create_daily_schedule():
    time_array = await get_time()
    asr_time = await round_time(time_array[2])
    maghrib_time = await round_time(time_array[3])
    asr_time_min = asr_time[1]
    maghrib_time_min = maghrib_time[1]
    if asr_time[1] < 10:
        asr_time_min = "0" + str(asr_time[1])
    if maghrib_time[1] < 10:
        maghrib_time_min = "0" + str(maghrib_time[1])
    #костыль на +5 мин магриб
    schedule_str = (f"📆 Время намаза\n\n"
                    f"🌅 Фаджр(Багымдат): {time_array[0]}\n"
                    f"☀️ Зухр(Бешим): {time_array[1]}\n"
                    f"⛅ Аср: {time_array[2]} (Сбор {asr_time[0]}:{asr_time_min})\n"
                    f"🌇 Магриб(Шам): {time_array[3]} (Сбор {maghrib_time[0]}:{maghrib_time_min})\n"
                    f"🌙 Иша(Куптан): {time_array[4]}")

    TimeHolder.time_schedule = schedule_str
    await send_time()
    run_time_asr = datetime.now().replace(hour=asr_time[2], minute=asr_time[3], second=0, microsecond=0)
    run_time_maghrib = datetime.now().replace(hour=maghrib_time[2], minute=maghrib_time[3], second=0, microsecond=0)
    scheduler.add_job(send_notification, "date", run_date=run_time_asr, args=[asr_time[0], asr_time_min])
    scheduler.add_job(send_notification, "date", run_date=run_time_maghrib, args=[maghrib_time[0], maghrib_time_min])


# Хэндлер на команду /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.username != "NUR_dametov":
        return
    await create_daily_schedule()


@dp.message(Command("time"))
async def cmd_time(message: types.Message):
    await message.answer(TimeHolder.time_schedule)


# Запуск процесса поллинга новых апдейтов
async def main():
    scheduler.add_job(create_daily_schedule, "cron", hour=9, minute=0)
    scheduler.start()
    jobs = scheduler.get_jobs()
    print(jobs)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
