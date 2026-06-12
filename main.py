#!/usr/bin/env python3
import asyncio, logging, signal, os
from aiogram import Bot, Dispatcher, Router
from aiogram.types import BotCommand
from telethon import TelegramClient
from config import Config
from database import Database
from downloader import MediaDownloader
from uploader import MediaUploader
from crawler import CrawlerManager
from handlers import register_handlers
from dependencies import set_dependencies
import ffmpeg_utils

logging.basicConfig(level=getattr(logging, Config.LOG_LEVEL), format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

download_queue = asyncio.Queue()

async def download_worker(db, downloader, uploader, wid):
    logger.info(f"Worker {wid} started")
    while True:
        try:
            mid = await download_queue.get()
            media = await db.fetch_one("SELECT source_url, title, job_id, retries FROM media WHERE id=?", (mid,))
            if not media:
                download_queue.task_done()
                continue
            url, title, job_id, retries = media["source_url"], media["title"], media["job_id"], media["retries"]
            if retries >= Config.DOWNLOAD_RETRIES:
                await db.update_media_status(mid, "failed", error="Max retries")
                download_queue.task_done()
                continue
            await db.update_media_status(mid, "downloading")
            try:
                local = await downloader.download(url)
                if not await ffmpeg_utils.verify_integrity(local):
                    raise Exception("Integrity failed")
                dur, w, h = await ffmpeg_utils.extract_metadata(local)
                thumb = os.path.join(Config.THUMBNAIL_DIR, f"{mid}.jpg")
                await ffmpeg_utils.generate_thumbnail(local, thumb)
                await db.update_media_status(mid, "processed", local_path=local, duration=dur, width=w, height=h, thumbnail_path=thumb)
                job = await db.get_job(job_id)
                if not job:
                    raise Exception("Job missing")
                chat = Config.TARGET_CHAT_ID if Config.TARGET_CHAT_ID != 0 else job["user_id"]
                msg_id = await uploader.upload_to_telegram(chat, local, thumb, f"📹 {title or url[:50]}", dur, w, h)
                if msg_id:
                    await db.execute("INSERT INTO uploads (media_id, telegram_message_id, telegram_chat_id, method) VALUES (?,?,?,?)",
                                     (mid, msg_id, chat, "bot_api" if os.path.getsize(local)<=50*1024*1024 else "telethon"))
                    await db.execute("UPDATE jobs SET media_uploaded = media_uploaded+1 WHERE id=?", (job_id,))
                    await db.commit()
                    logger.info(f"Uploaded {mid}")
                # cleanup
                if os.path.exists(local): os.remove(local)
                if os.path.exists(thumb): os.remove(thumb)
            except Exception as e:
                logger.error(f"Failed {mid}: {e}")
                await db.update_media_status(mid, "pending", error=str(e), inc_retry=True)
                await download_queue.put(mid)
            finally:
                download_queue.task_done()
        except Exception as e:
            logger.exception(f"Worker {wid} error")
            await asyncio.sleep(1)

async def set_commands(bot):
    await bot.set_my_commands([
        BotCommand("start","Help"), BotCommand("scan","Start crawl"), BotCommand("stop","Pause"),
        BotCommand("resume","Resume"), BotCommand("status","Job status"), BotCommand("stats","Your stats"),
        BotCommand("queue","Pending media")
    ])

async def main():
    Config.validate()
    os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)
    os.makedirs(Config.THUMBNAIL_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    db = Database()
    await db.init()
    logger.info("DB ready")
    bot = Bot(token=Config.BOT_TOKEN)
    tele = None
    try:
        tele = TelegramClient("telethon_session", Config.API_ID, Config.API_HASH)
        await tele.start()
        logger.info("Telethon ready")
    except Exception as e:
        logger.warning(f"Telethon failed: {e}")
    uploader = MediaUploader(bot, tele)
    downloader = MediaDownloader()
    cm = CrawlerManager(db, download_queue)
    dp = Dispatcher()
    dp["db"] = db
    dp["crawler_mgr"] = cm
    set_dependencies(dp)
    router = Router()
    register_handlers(router)
    dp.include_router(router)
    workers = [asyncio.create_task(download_worker(db, downloader, uploader, i)) for i in range(Config.MAX_CONCURRENT_DOWNLOADS)]
    logger.info(f"Started {Config.MAX_CONCURRENT_DOWNLOADS} workers")
    await set_commands(bot)
    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        asyncio.get_running_loop().add_signal_handler(sig, stop.set)
    logger.info("Bot running")
    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        for w in workers: w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
        if tele: await tele.disconnect()
        await db.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
