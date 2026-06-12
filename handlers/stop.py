from aiogram import Router, types
from aiogram.filters import Command
from config import Config
from dependencies import get_db, get_crawler_mgr
router = Router()

@router.message(Command("stop"))
async def cmd_stop(m: types.Message):
    if m.from_user.id not in Config.TELEGRAM_USER_IDS:
        await m.reply("Unauthorized")
        return
    db = get_db()
    cm = get_crawler_mgr()
    job = await db.get_running_job_for_user(m.from_user.id)
    if not job:
        await m.reply("No running job")
        return
    if await cm.stop_crawl(job["id"]):
        await db.update_job_status(job["id"], "paused")
        await m.reply(f"Job #{job['id']} paused.")
    else:
        await m.reply("Could not pause.")
