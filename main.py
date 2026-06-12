#!/usr/bin/env python3
import asyncio
import logging
import signal
import os
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

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

download_queue = asyncio.Queue()

async def download_worker(db, downloader, uploader, wid):
    logger.info(f"Worker {wid} started")
    while True:
        try:
            mid = await download_queue.get()
            media = await db.fetch_one(
                "SELECT source_url, title, job_id, retries FROM media WHERE id=?",
                (mid,)
            )
            if not media:
                download_queue.task_done()
                continue

            url = media["source_url"]
            title = media["title"]
            job_id = media["job_id"]
            retries = media["retries"]

            if retries >= Config.DOWNLOAD_RETRIES:
                await db.update_media_status(mid, "failed", error="Max retries exceeded")
                download_queue.task_done()
                continue

            await db.update_media_status(mid, "downloading")

            try:
                local_path = await downloader.download(url)
                if not await ffmpeg_utils.verify_integrity(local_path):
                    raise Exception("File integrity failed")

                duration, width, height = await ffmpeg_utils.extract_metadata(local_path)
                thumb_path = os.path.join(Config.THUMBNAIL_DIR, f"{mid}.jpg")
                await ffmpeg_utils.generate_thumbnail(local_path, thumb_path)

                await db.update_media_status(
                    mid, "processed",
                    local_path=local_path,
                    duration=duration, width=width, height=height,
                    thumbnail_path=thumb_path
                )

                job = await db.get_job(job_id)
                if not job:
                    raise Exception("Job not found")

                target_chat = Config.TARGET_CHAT_ID if Config.TARGET_CHAT_ID != 0 else job["user_id"]

                msg_id = await uploader.upload_to_telegram(
                    chat_id=target_chat,
                    media_path=local_path,
                    thumbnail_path=thumb_path,
                    caption=f"📹 {title or url[:50]}",
                    duration=duration, width=width, height=height
                )

                if msg_id:
                    await db.execute(
                        "INSERT INTO uploads (media_id, telegram_message_id, telegram_chat_id, method) VALUES (?,?,?,?)",
                        (mid, msg_id, target_chat, "bot_api" if os.path.getsize(local_path) <= 50*1024*1024 else "telethon")
                    )
                    await db.execute("UPDATE jobs SET media_uploaded = media_uploaded+1 WHERE id=?", (job_id,))
                    await db.commit()
                    logger.info(f"Uploaded {mid}")

                # Cleanup
                if os.path.exists(local_path):
                    os.remove(local_path)
                if os.path.exists(thumb_path):
                    os.remove(thumb_path)

            except Exception as e:
                logger.error(f"Failed {mid}: {e}")
                await db.update_media_status(mid, "pending", error=str(e), inc_retry=True)
                await download_queue.put(mid)  # Requeue

            finally:
                download_queue.task_done()

        except Exception as e:
            logger.exception(f"Worker {wid} error")
            await asyncio.sleep(1)

async def set_commands(bot: Bot):
    await bot.set_my_commands([
        BotCommand(command="start", description="Show help"),
        BotCommand(command="scan", description="Start crawling a website"),
        BotCommand(command="stop", description="Pause current crawl"),
        BotCommand(command="resume", description="Resume paused crawl"),
        BotCommand(command="status", description="Show current job status"),
        BotCommand(command="stats", description="Show your statistics"),
        BotCommand(command="queue", description="Show pending media count"),
    ])

async def main():
    # Validate config
    Config.validate()

    # Create directories
    os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)
    os.makedirs(Config.THUMBNAIL_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)

    # Database
    db = Database()
    await db.init()
    logger.info("DB ready")

    # Bot
    bot = Bot(token=Config.BOT_TOKEN)

    # Telethon (optional)
    telethon_client = None
    try:
        telethon_client = TelegramClient("telethon_session", Config.API_ID, Config.API_HASH)
        await telethon_client.start()
        logger.info("Telethon ready")
    except Exception as e:
        logger.warning(f"Telethon failed: {e}. Large file uploads disabled.")

    # Components
    uploader = MediaUploader(bot, telethon_client)
    downloader = MediaDownloader()
    crawler_mgr = CrawlerManager(db, download_queue)

    # Dispatcher and dependencies
    dp = Dispatcher()
    dp["db"] = db
    dp["crawler_mgr"] = crawler_mgr
    set_dependencies(dp)

    # Router and handlers
    router = Router()
    register_handlers(router)
    dp.include_router(router)

    # Workers
    workers = []
    for i in range(Config.MAX_CONCURRENT_DOWNLOADS):
        workers.append(asyncio.create_task(download_worker(db, downloader, uploader, i)))
    logger.info(f"Started {Config.MAX_CONCURRENT_DOWNLOADS} workers")

    # Bot commands menu
    await set_commands(bot)

    # Graceful shutdown
    stop_signal = asyncio.Event()

    def signal_handler():
        logger.info("Shutdown signal received")
        stop_signal.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        asyncio.get_running_loop().add_signal_handler(sig, signal_handler)

    logger.info("Bot is running. Press Ctrl+C to stop.")

    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        logger.info("Shutting down...")
        for w in workers:
            w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
        if telethon_client:
            await telethon_client.disconnect()
        await db.close()
        await bot.session.close()
        logger.info("Shutdown complete")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
