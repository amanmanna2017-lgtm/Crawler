from aiogram import Router, types
from aiogram.filters import Command
from config import Config
from dependencies import get_db
router = Router()

@router.message(Command("status"))
async def cmd_status(m: types.Message):
    if m.from_user.id not in Config.TELEGRAM_USER_IDS:
        await m.reply("Unauthorized")
        return
    db = get_db()
    job = await db.get_running_job_for_user(m.from_user.id)
    if not job:
        await m.reply("No active job")
        return
    await m.reply(f"*Job #{job['id']}*\nStatus: {job['status']}\nPages: {job['pages_crawled']}\nMedia found: {job['media_found']}\nUploaded: {job['media_uploaded']}", parse_mode="MarkdownV2")
