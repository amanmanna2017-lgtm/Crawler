import asyncio
from telethon import TelegramClient
from config import Config

async def main():
    print("Login to Telegram for large file uploads...")
    client = TelegramClient("telethon_session", Config.API_ID, Config.API_HASH)
    await client.start()
    me = await client.get_me()
    print(f"Logged in as {me.username or me.first_name}")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
