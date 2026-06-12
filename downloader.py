import asyncio
import aiohttp
import aiofiles
import os
import re
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from config import Config

class DownloadError(Exception):
    pass

def is_retryable(e):
    return isinstance(e, (aiohttp.ClientError, asyncio.TimeoutError, DownloadError))

class MediaDownloader:
    def __init__(self, download_dir=Config.DOWNLOAD_DIR):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)

    @retry(stop=stop_after_attempt(Config.DOWNLOAD_RETRIES),
           wait=wait_exponential(multiplier=Config.RETRY_BACKOFF_BASE, min=2, max=30),
           retry=retry_if_exception(is_retryable))
    async def download(self, url, filename=None):
        if not filename:
            safe = re.sub(r'[^\\w\\-_.]', '_', url.split("/")[-1].split("?")[0]) or "media"
            filename = f"{safe}_{abs(hash(url)) % 10000}.mp4"
        path = os.path.join(self.download_dir, filename)
        timeout = aiohttp.ClientTimeout(total=300)
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            async with sess.get(url) as resp:
                if resp.status != 200:
                    raise DownloadError(f"HTTP {resp.status}")
                async with aiofiles.open(path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(8192):
                        await f.write(chunk)
        return path
