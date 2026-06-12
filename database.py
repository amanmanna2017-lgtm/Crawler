import aiosqlite
import json
from typing import Optional, List, Dict
from config import Config

class Database:
    def __init__(self, db_path=Config.DATABASE_PATH):
        self.db_path = db_path
        self.conn = None

    async def init(self):
        self.conn = await aiosqlite.connect(self.db_path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.executescript("""
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
                media_uploaded INTEGER DEFAULT 0,
                current_urls TEXT DEFAULT '[]',
                crawled_urls TEXT DEFAULT '[]'
            );
            CREATE TABLE IF NOT EXISTS pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                title TEXT,
                depth INTEGER DEFAULT 0,
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
                retries INTEGER DEFAULT 0,
                UNIQUE(job_id, source_url)
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
        await self.conn.commit()

    async def close(self):
        if self.conn:
            await self.conn.close()

    async def execute(self, query, params=()):
        return await self.conn.execute(query, params)

    async def commit(self):
        await self.conn.commit()

    async def fetch_one(self, query, params=()):
        cur = await self.conn.execute(query, params)
        row = await cur.fetchone()
        return dict(row) if row else None

    async def fetch_all(self, query, params=()):
        cur = await self.conn.execute(query, params)
        rows = await cur.fetchall()
        return [dict(row) for row in rows]

    async def create_job(self, user_id, root_url, max_depth):
        cur = await self.conn.execute(
            "INSERT INTO jobs (user_id, root_url, max_depth, current_urls) VALUES (?, ?, ?, ?)",
            (user_id, root_url, max_depth, json.dumps([(root_url, 0)]))
        )
        await self.commit()
        return cur.lastrowid

    async def update_job_status(self, job_id, status):
        await self.conn.execute(
            "UPDATE jobs SET status = ?, completed_at = CASE WHEN ? IN ('completed','stopped','failed') THEN CURRENT_TIMESTAMP ELSE completed_at END WHERE id = ?",
            (status, status, job_id)
        )
        await self.commit()

    async def add_page(self, job_id, url, title="", depth=0):
        try:
            await self.conn.execute(
                "INSERT INTO pages (job_id, url, title, depth) VALUES (?, ?, ?, ?)",
                (job_id, url, title, depth)
            )
            await self.commit()
            await self.conn.execute("UPDATE jobs SET pages_crawled = pages_crawled + 1 WHERE id = ?", (job_id,))
            await self.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

    async def is_page_visited(self, job_id, url):
        cur = await self.conn.execute("SELECT 1 FROM pages WHERE job_id = ? AND url = ?", (job_id, url))
        return await cur.fetchone() is not None

    async def add_media(self, job_id, page_url, source_url, title=""):
        try:
            cur = await self.conn.execute(
                "INSERT INTO media (job_id, page_url, source_url, title) VALUES (?, ?, ?, ?)",
                (job_id, page_url, source_url, title)
            )
            await self.commit()
            await self.conn.execute("UPDATE jobs SET media_found = media_found + 1 WHERE id = ?", (job_id,))
            await self.commit()
            return cur.lastrowid
        except aiosqlite.IntegrityError:
            return None

    async def get_pending_media(self, limit=10):
        return await self.fetch_all(
            "SELECT id, job_id, source_url, title, page_url, retries FROM media WHERE status = 'pending' LIMIT ?",
            (limit,)
        )

    async def update_media_status(self, media_id, status, local_path="", duration=0, width=0, height=0, thumbnail_path="", error="", inc_retry=False):
        if inc_retry:
            await self.conn.execute(
                "UPDATE media SET status=?, local_path=?, duration=?, width=?, height=?, thumbnail_path=?, error=?, retries=retries+1 WHERE id=?",
                (status, local_path, duration, width, height, thumbnail_path, error, media_id)
            )
        else:
            await self.conn.execute(
                "UPDATE media SET status=?, local_path=?, duration=?, width=?, height=?, thumbnail_path=?, error=? WHERE id=?",
                (status, local_path, duration, width, height, thumbnail_path, error, media_id)
            )
        await self.commit()

    async def get_job(self, job_id):
        return await self.fetch_one("SELECT * FROM jobs WHERE id = ?", (job_id,))

    async def get_running_job_for_user(self, user_id):
        return await self.fetch_one(
            "SELECT * FROM jobs WHERE user_id = ? AND status IN ('running', 'paused') ORDER BY id DESC LIMIT 1",
            (user_id,)
        )

    async def get_paused_job_for_user(self, user_id):
        return await self.fetch_one(
            "SELECT * FROM jobs WHERE user_id = ? AND status = 'paused' ORDER BY id DESC LIMIT 1",
            (user_id,)
        )

    async def get_stats(self, user_id):
        row = await self.fetch_one(
            "SELECT COUNT(*) as total_jobs, COALESCE(SUM(pages_crawled),0) as total_pages, COALESCE(SUM(media_found),0) as total_media, COALESCE(SUM(media_uploaded),0) as total_uploaded FROM jobs WHERE user_id = ?",
            (user_id,)
        )
        return row or {"total_jobs":0, "total_pages":0, "total_media":0, "total_uploaded":0}

    async def save_crawl_state(self, job_id, queue, visited):
        await self.conn.execute(
            "UPDATE jobs SET current_urls = ?, crawled_urls = ? WHERE id = ?",
            (json.dumps(queue), json.dumps(list(visited)), job_id)
        )
        await self.commit()

    async def get_crawl_state(self, job_id):
        job = await self.get_job(job_id)
        if job:
            current = json.loads(job.get("current_urls", "[]"))
            crawled = set(json.loads(job.get("crawled_urls", "[]")))
            return current, crawled
        return [], set()
