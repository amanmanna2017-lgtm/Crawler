from aiogram import Router, types
from aiogram.filters import Command
from config import Config
from dependencies import get_db

router = Router()

@router.message(Command("stats"))
async def cmd_stats(m: types.Message):
    if m.from_user.id not in Config.TELEGRAM_USER_IDS:
        await m.reply("Unauthorized")
        return
    db = get_db()
    s = await db.get_stats(m.from_user.id)
    await m.reply(f"📊 Total jobs: {s['total_jobs']}\nPages: {s['total_pages']}\nMedia: {s['total_media']}\nUploaded: {s['total_uploaded']}")
