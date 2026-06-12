import asyncio
from aiogram import Router, types
from aiogram.filters import Command
from config import Config
from dependencies import get_db, get_crawler_mgr
router = Router()

@router.message(Command("resume"))
async def cmd_resume(m: types.Message):
    if m.from_user.id not in Config.TELEGRAM_USER_IDS:
        await m.reply("Unauthorized")
        return
    db = get_db()
    cm = get_crawler_mgr()
    job = await db.get_paused_job_for_user(m.from_user.id)
    if not job:
        await m.reply("No paused job")
        return
    await db.update_job_status(job["id"], "running")
    asyncio.create_task(cm.start_crawl(job["id"], job["root_url"], job["max_depth"], m.from_user.id))
    await m.reply(f"Resuming job #{job['id']}")
