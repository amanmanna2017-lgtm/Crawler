from aiogram import Router, types
from aiogram.filters import Command
router = Router()

@router.message(Command("start"))
async def cmd_start(m: types.Message):
    await m.answer("🤖 *Website Archiver Bot*\n\nCommands:\n/scan <url> [depth]\n/stop\n/resume\n/status\n/stats\n/queue", parse_mode="MarkdownV2")
