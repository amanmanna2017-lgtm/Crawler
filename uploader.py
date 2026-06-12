import os
from aiogram import Bot
from telethon import TelegramClient
from telethon.tl.types import DocumentAttributeVideo

class MediaUploader:
    def __init__(self, bot: Bot, telethon_client):
        self.bot = bot
        self.telethon = telethon_client

    async def upload_to_telegram(self, chat_id, media_path, thumbnail_path=None, caption="", duration=0, width=0, height=0):
        size = os.path.getsize(media_path)
        if size <= 50 * 1024 * 1024:
            return await self._upload_via_bot_api(chat_id, media_path, thumbnail_path, caption, duration, width, height)
        else:
            if self.telethon is None:
                print("Telethon not available")
                return None
            return await self._upload_via_telethon(chat_id, media_path, thumbnail_path, caption, duration, width, height)

    async def _upload_via_bot_api(self, chat_id, media_path, thumb_path, caption, duration, width, height):
        try:
            with open(media_path, "rb") as vid:
                if thumb_path and os.path.exists(thumb_path):
                    with open(thumb_path, "rb") as thumb:
                        msg = await self.bot.send_video(chat_id, video=vid, thumbnail=thumb, caption=caption[:1024],
                                                        duration=duration, width=width, height=height, supports_streaming=True)
                else:
                    msg = await self.bot.send_video(chat_id, video=vid, caption=caption[:1024],
                                                    duration=duration, width=width, height=height, supports_streaming=True)
            return msg.message_id
        except Exception as e:
            print(f"Bot API upload error: {e}")
            return None

    async def _upload_via_telethon(self, chat_id, media_path, thumb_path, caption, duration, width, height):
        try:
            file = await self.telethon.upload_file(media_path)
            thumb = None
            if thumb_path and os.path.exists(thumb_path):
                thumb = await self.telethon.upload_file(thumb_path)
            msg = await self.telethon.send_file(chat_id, file, caption=caption[:1024], thumb=thumb, video_note=False,
                                                attributes=[DocumentAttributeVideo(duration=duration, w=width, h=height, supports_streaming=True)])
            return msg.id
        except Exception as e:
            print(f"Telethon upload error: {e}")
            return None
