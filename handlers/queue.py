from aiogram import Router, types
from aiogram.filters import Command
from config import Config
from dependencies import get_db
router = Router()

@router.message(Command("queue"))
async def cmd_queue(m: types.Message):
    if m.from_user.id not in Config.TELEGRAM_USER_IDS:
        await m.reply("Unauthorized")
        return
    db = get_db()
    pending = await db.get_pending_media(limit=1000)
    await m.reply(f"Pending media: {len(pending)}")
