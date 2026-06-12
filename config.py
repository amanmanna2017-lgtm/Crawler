import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    API_ID = int(os.getenv("API_ID", 0))
    API_HASH = os.getenv("API_HASH", "")
    TELEGRAM_USER_IDS = [int(x) for x in os.getenv("TELEGRAM_USER_IDS", "").split(",") if x]
    TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID", "0"))

    DATABASE_PATH = os.getenv("DATABASE_PATH", "data/bot.db")
    DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "data/downloads")
    THUMBNAIL_DIR = os.getenv("THUMBNAIL_DIR", "data/thumbnails")

    MAX_CRAWL_DEPTH = int(os.getenv("MAX_CRAWL_DEPTH", 2))
    CRAWL_TIMEOUT = int(os.getenv("CRAWL_TIMEOUT", 30))
    MAX_CONCURRENT_DOWNLOADS = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", 3))
    DOWNLOAD_RETRIES = int(os.getenv("DOWNLOAD_RETRIES", 3))
    RETRY_BACKOFF_BASE = int(os.getenv("RETRY_BACKOFF_BASE", 2))

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls):
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN missing")
        if not cls.API_ID or not cls.API_HASH:
            raise ValueError("API_ID/API_HASH missing")
        if not cls.TELEGRAM_USER_IDS:
            raise ValueError("TELEGRAM_USER_IDS empty")
