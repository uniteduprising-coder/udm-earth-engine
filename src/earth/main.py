from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from earth.api.advantage_routes import router as advantage_router
from earth.api.toroidal_routes import router as toroidal_router
from earth.api.cosmology_routes import bake_public_assets, router as cosmology_router
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
    try:
        bake_public_assets()
    except Exception:
        pass
    _scheduler = FeedScheduler()
    _scheduler.start()
    asyncio.create_task(_scheduler.refresh_all())
    yield
    if _scheduler.scheduler.running:
        _scheduler.scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="UDM Earth Engine", version="5.2.1", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix="/api")
    app.include_router(cosmology_router, prefix="/api")
    app.include_router(advantage_router, prefix="/api")
    app.include_router(toroidal_router, prefix="/api")
    app.include_router(router)
    app.include_router(cosmology_router)
    app.include_router(advantage_router)
    app.include_router(toroidal_router)

    public = ROOT / "public"
    if public.exists():
        app.mount("/data", StaticFiles(directory=public / "data"), name="data")
        app.mount("/assets", StaticFiles(directory=public / "assets"), name="assets")

    @app.get("/")
    async def index():
        path = public / "index.html"
        if path.exists():
            return FileResponse(path)
        return {"service": "udm-earth-engine", "ui": "public/index.html missing"}

    @app.get("/embed")
    async def embed():
        path = public / "index.html"
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