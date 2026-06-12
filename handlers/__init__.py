from aiogram import Router
def register_handlers(router: Router):
    from . import start, scan, stop, status, stats, resume, queue
    router.include_router(start.router)
    router.include_router(scan.router)
    router.include_router(stop.router)
    router.include_router(status.router)
    router.include_router(stats.router)
    router.include_router(resume.router)
    router.include_router(queue.router)
