from aiogram import Router, types
from aiogram.filters import Command

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🤖 *Website Archiver Bot*\n\n"
        "Commands:\n"
        "/scan \\<url\\> [depth] - Start crawling\n"
        "/stop - Pause current crawl\n"
        "/resume - Resume paused crawl\n"
        "/status - Show job status\n"
        "/stats - Your statistics\n"
        "/queue - Pending media count\n\n"
        "Example: `/scan https://example.com 2`",
        parse_mode="MarkdownV2"
    )
