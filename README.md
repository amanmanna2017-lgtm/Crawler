# Telegram Archiver Bot

Crawl websites, detect videos (MP4, M3U8, video tags), download and upload to Telegram. Supports large files via Telethon.

## Deploy on VPS

```bash
git clone https://github.com/YOUR_USERNAME/telegram-archiver.git
cd telegram-archiver
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env   # add bot token, API ID, API HASH, your user ID
python setup_telethon.py   # one-time login
python main.py
