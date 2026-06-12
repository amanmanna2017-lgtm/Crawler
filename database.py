-- pages: store visited pages per crawl job
CREATE TABLE IF NOT EXISTS pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    title TEXT,
    visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(job_id, url)
);

-- media: discovered media items
CREATE TABLE IF NOT EXISTS media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    page_url TEXT NOT NULL,
    source_url TEXT NOT NULL,
    title TEXT,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending',   -- pending, downloading, processed, failed
    local_path TEXT,
    duration INTEGER,
    width INTEGER,
    height INTEGER,
    thumbnail_path TEXT,
    error TEXT,
    retries INTEGER DEFAULT 0
);

-- jobs: crawling jobs
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    root_url TEXT NOT NULL,
    max_depth INTEGER NOT NULL,
    status TEXT DEFAULT 'running',   -- running, paused, completed, failed, stopped
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    pages_crawled INTEGER DEFAULT 0,
    media_found INTEGER DEFAULT 0,
    media_uploaded INTEGER DEFAULT 0
);

-- uploads: Telethon/Bot API upload records
CREATE TABLE IF NOT EXISTS uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id INTEGER NOT NULL,
    telegram_message_id INTEGER,
    telegram_chat_id INTEGER,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    method TEXT   -- 'bot_api' or 'telethon'
);
