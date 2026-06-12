from aiogram import Dispatcher
_dp = None

def set_dependencies(dp: Dispatcher):
    global _dp
    _dp = dp

def get_db():
    return _dp["db"]

def get_crawler_mgr():
    return _dp["crawler_mgr"]
