import asyncio
import aiosqlite
from typing import Optional, List, Dict, Any
from datetime import datetime
from config import Config

class Database:
    def __init__(self, db_path: str = Config.DATABASE_PATH):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def init(self) -> None:
        self._conn = await aiosqlite.connect(self.db_path)
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                title TEXT,
                visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(job_id, url)
            );
            CREATE TABLE IF NOT EXISTS media (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                page_url TEXT NOT NULL,
                source_url TEXT NOT NULL,
                title TEXT,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',
                local_path TEXT,
                duration INTEGER,
                width INTEGER,
                height INTEGER,
                thumbnail_path TEXT,
                error TEXT,
                retries INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                root_url TEXT NOT NULL,
                max_depth INTEGER NOT NULL,
                status TEXT DEFAULT 'running',
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                pages_crawled INTEGER DEFAULT 0,
                media_found INTEGER DEFAULT 0,
                media_uploaded INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                media_id INTEGER NOT NULL,
                telegram_message_id INTEGER,
                telegram_chat_id INTEGER,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                method TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_pages_job_url ON pages(job_id, url);
            CREATE INDEX IF NOT EXISTS idx_media_job_status ON media(job_id, status);
            CREATE INDEX IF NOT EXISTS idx_jobs_user_status ON jobs(user_id, status);
        """)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()

    async def create_job(self, user_id: int, root_url: str, max_depth: int) -> int:
        cur = await self._conn.execute(
            "INSERT INTO jobs (user_id, root_url, max_depth) VALUES (?, ?, ?)",
            (user_id, root_url, max_depth)
        )
        await self._conn.commit()
        return cur.lastrowid

    async def update_job_status(self, job_id: int, status: str) -> None:
        await self._conn.execute(
            "UPDATE jobs SET status = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, job_id)
        )
        await self._conn.commit()

    async def add_page(self, job_id: int, url: str, title: str = "") -> bool:
        try:
            await self._conn.execute(
                "INSERT INTO pages (job_id, url, title) VALUES (?, ?, ?)",
                (job_id, url, title)
            )
            await self._conn.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

    async def is_page_visited(self, job_id: int, url: str) -> bool:
        cur = await self._conn.execute(
            "SELECT 1 FROM pages WHERE job_id = ? AND url = ?", (job_id, url)
        )
        return await cur.fetchone() is not None

    async def add_media(self, job_id: int, page_url: str, source_url: str, title: str = "") -> int:
        cur = await self._conn.execute(
            "INSERT INTO media (job_id, page_url, source_url, title) VALUES (?, ?, ?, ?)",
            (job_id, page_url, source_url, title)
        )
        await self._conn.commit()
        # increment media_found in job
        await self._conn.execute(
            "UPDATE jobs SET media_found = media_found + 1 WHERE id = ?", (job_id,)
        )
        await self._conn.commit()
        return cur.lastrowid

    async def get_pending_media(self, limit: int = 10) -> List[Dict[str, Any]]:
        cur = await self._conn.execute(
            "SELECT id, job_id, source_url, title, page_url, retries FROM media WHERE status = 'pending' LIMIT ?",
            (limit,)
        )
        rows = await cur.fetchall()
        return [dict(row) for row in rows]

    async def update_media_status(
        self, media_id: int, status: str, local_path: str = "",
        duration: int = 0, width: int = 0, height: int = 0,
        thumbnail_path: str = "", error: str = "", inc_retry: bool = False
    ) -> None:
        if inc_retry:
            await self._conn.execute(
                "UPDATE media SET status = ?, local_path = ?, duration = ?, width = ?, height = ?, thumbnail_path = ?, error = ?, retries = retries + 1 WHERE id = ?",
                (status, local_path, duration, width, height, thumbnail_path, error, media_id)
            )
        else:
            await self._conn.execute(
                "UPDATE media SET status = ?, local_path = ?, duration = ?, width = ?, height = ?, thumbnail_path = ?, error = ? WHERE id = ?",
                (status, local_path, duration, width, height, thumbnail_path, error, media_id)
            )
        await self._conn.commit()

    async def get_job(self, job_id: int) -> Optional[Dict[str, Any]]:
        cur = await self._conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = await cur.fetchone()
        return dict(row) if row else None

    async def get_running_job_for_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        cur = await self._conn.execute(
            "SELECT * FROM jobs WHERE user_id = ? AND status IN ('running', 'paused') ORDER BY id DESC LIMIT 1",
            (user_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def get_stats(self, user_id: int) -> Dict[str, int]:
        cur = await self._conn.execute(
            "SELECT COUNT(*) as total_jobs, SUM(pages_crawled) as total_pages, SUM(media_found) as total_media, SUM(media_uploaded) as total_uploaded FROM jobs WHERE user_id = ?",
            (user_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else {"total_jobs": 0, "total_pages": 0, "total_media": 0, "total_uploaded": 0}
