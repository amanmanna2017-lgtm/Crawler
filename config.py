import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    API_ID: int = int(os.getenv("API_ID", 0))
    API_HASH: str = os.getenv("API_HASH", "")
    TELEGRAM_USER_IDS: list[int] = [int(x) for x in os.getenv("TELEGRAM_USER_IDS", "").split(",") if x]

    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/bot.db")
    DOWNLOAD_DIR: str = os.getenv("DOWNLOAD_DIR", "data/downloads")
    THUMBNAIL_DIR: str = os.getenv("THUMBNAIL_DIR", "data/thumbnails")

    MAX_CRAWL_DEPTH: int = int(os.getenv("MAX_CRAWL_DEPTH", 2))
    RESPECT_ROBOTS_TXT: bool = os.getenv("RESPECT_ROBOTS_TXT", "True").lower() == "true"
    CRAWL_TIMEOUT: int = int(os.getenv("CRAWL_TIMEOUT", 30))

    MAX_CONCURRENT_DOWNLOADS: int = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", 3))
    DOWNLOAD_RETRIES: int = int(os.getenv("DOWNLOAD_RETRIES", 3))
    RETRY_BACKOFF_BASE: int = int(os.getenv("RETRY_BACKOFF_BASE", 2))

    TELEGRAM_MAX_FILE_SIZE_BOT_API: int = int(os.getenv("TELEGRAM_MAX_FILE_SIZE_BOT_API", 52428800))

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls) -> None:
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN missing")
        if not cls.API_ID or not cls.API_HASH:
            raise ValueError("API_ID/API_HASH missing for Telethon")
        if not cls.TELEGRAM_USER_IDS:
            raise ValueError("TELEGRAM_USER_IDS empty")
