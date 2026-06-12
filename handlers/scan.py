import asyncio
from aiogram import Router, types
from aiogram.filters import Command
from urllib.parse import urlparse
from config import Config
from dependencies import get_db, get_crawler_mgr
router = Router()

@router.message(Command("scan"))
async def cmd_scan(m: types.Message):
    if m.from_user.id not in Config.TELEGRAM_USER_IDS:
        await m.reply("Unauthorized")
        return
    db = get_db()
    cm = get_crawler_mgr()
    parts = m.text.split(maxsplit=2)
    if len(parts) < 2:
        await m.reply("Usage: /scan <url> [depth]")
        return
    url = parts[1]
    depth = Config.MAX_CRAWL_DEPTH
    if len(parts)==3 and parts[2].isdigit():
        depth = int(parts[2])
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        await m.reply("Invalid URL")
        return
    existing = await db.get_running_job_for_user(m.from_user.id)
    if existing:
        await m.reply(f"Job #{existing['id']} already running. Use /stop first.")
        return
    job_id = await db.create_job(m.from_user.id, url, depth)
    await m.reply(f"Crawl started. Job ID: {job_id}\nDepth: {depth}")
    asyncio.create_task(cm.start_crawl(job_id, url, depth, m.from_user.id))
