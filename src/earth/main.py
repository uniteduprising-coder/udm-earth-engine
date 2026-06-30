from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from earth.api.routes import router
from earth.config import ROOT, get_settings
from earth.scheduler import FeedScheduler

_scheduler: FeedScheduler | None = None


def get_scheduler() -> FeedScheduler | None:
    return _scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    global _scheduler
    _scheduler = FeedScheduler()
    _scheduler.start()
    asyncio.create_task(_scheduler.refresh_all())
    yield
    if _scheduler.scheduler.running:
        _scheduler.scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="UDM Earth Engine", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    frontend = ROOT / "frontend"
    assets = frontend / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/")
    async def index():
        path = frontend / "index.html"
        if path.exists():
            return FileResponse(path)
        return {"service": "udm-earth-engine", "ui": "frontend/index.html missing"}

    @app.get("/embed")
    async def embed():
        path = frontend / "index.html"
        if path.exists():
            return FileResponse(path)
        return {"service": "udm-earth-engine", "embed": True}

    return app


app = create_app()


def main() -> None:
    s = get_settings()
    uvicorn.run("earth.main:app", host=s.app_host, port=s.app_port, reload=s.app_env == "development")


if __name__ == "__main__":
    main()