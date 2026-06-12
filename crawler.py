import asyncio
import aiohttp
from urllib.parse import urljoin, urlparse, urlunparse
from bs4 import BeautifulSoup
from config import Config
from database import Database

class CrawlerManager:
    def __init__(self, db: Database, download_queue: asyncio.Queue):
        self.db = db
        self.download_queue = download_queue
        self.active = {}
        self.stop_flags = {}

    async def start_crawl(self, job_id, root_url, max_depth, user_id):
        self.stop_flags[job_id] = False
        task = asyncio.create_task(self._run(job_id, root_url, max_depth))
        self.active[job_id] = task
        try:
            await task
        except asyncio.CancelledError:
            await self.db.update_job_status(job_id, "paused")
        finally:
            self.active.pop(job_id, None)
            self.stop_flags.pop(job_id, None)

    async def stop_crawl(self, job_id):
        if job_id in self.active:
            self.stop_flags[job_id] = True
            self.active[job_id].cancel()
            return True
        return False

    async def _run(self, job_id, root_url, max_depth):
        parsed = urlparse(root_url)
        base_domain = parsed.netloc
        queue, visited = await self.db.get_crawl_state(job_id)
        if not queue:
            queue = [(root_url, 0)]
            visited = set()
        async with aiohttp.ClientSession() as session:
            while queue and not self.stop_flags.get(job_id, False):
                if len(queue) % 10 == 0:
                    await self.db.save_crawl_state(job_id, queue, visited)
                url, depth = queue.pop(0)
                if url in visited or depth > max_depth:
                    continue
                visited.add(url)
                try:
                    new_urls, media_urls = await self._crawl_page(session, job_id, url, base_domain, depth)
                    for nu, nd in new_urls:
                        if nu not in visited:
                            queue.append((nu, nd))
                    for mu in media_urls:
                        mid = await self.db.add_media(job_id, url, mu, "Discovered")
                        if mid:
                            await self.download_queue.put(mid)
                except Exception as e:
                    print(f"Error {url}: {e}")
                await asyncio.sleep(0.5)
        job = await self.db.get_job(job_id)
        if job and job["status"] == "running":
            await self.db.update_job_status(job_id, "completed")

    async def _crawl_page(self, session, job_id, url, base_domain, depth):
        timeout = aiohttp.ClientTimeout(total=Config.CRAWL_TIMEOUT)
        new_urls = []
        media_urls = set()
        try:
            async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=timeout) as resp:
                if resp.status != 200:
                    return new_urls, media_urls
                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')
                title = soup.title.string if soup.title else url
                await self.db.add_page(job_id, url, title, depth)
                # video tags
                for vid in soup.find_all('video'):
                    src = vid.get('src')
                    if src:
                        media_urls.add(urljoin(url, src))
                    for src in vid.find_all('source'):
                        s = src.get('src')
                        if s:
                            media_urls.add(urljoin(url, s))
                # direct links
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if any(href.lower().endswith(ext) for ext in ['.mp4','.m3u8','.webm','.mkv']):
                        media_urls.add(urljoin(url, href))
                # iframes
                for iframe in soup.find_all('iframe', src=True):
                    media_urls.add(iframe['src'])
                # same-domain links for crawling
                if depth < Config.MAX_CRAWL_DEPTH:
                    for a in soup.find_all('a', href=True):
                        full = urljoin(url, a['href'])
                        parsed = urlparse(full)
                        if parsed.netloc == base_domain or parsed.netloc == '':
                            full = urlunparse(parsed._replace(fragment=''))
                            if not await self.db.is_page_visited(job_id, full):
                                new_urls.append((full, depth+1))
                return new_urls, media_urls
        except Exception as e:
            print(f"Fetch error {url}: {e}")
            return new_urls, media_urls
