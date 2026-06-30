from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from earth.api.advantage_routes import router as advantage_router
from earth.api.celestial_routes import router as celestial_router
from earth.api.procedural_routes import router as procedural_router
from earth.api.simulation_routes import router as simulation_router
from earth.api.realtime_routes import router as realtime_router
from earth.api.encyclopedia_routes import router as encyclopedia_router
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
    app.include_router(encyclopedia_router, prefix="/api")
    app.include_router(celestial_router, prefix="/api")
    app.include_router(realtime_router, prefix="/api")
    app.include_router(procedural_router, prefix="/api")
    app.include_router(simulation_router, prefix="/api")
    app.include_router(router)
    app.include_router(cosmology_router)
    app.include_router(advantage_router)
    app.include_router(toroidal_router)
    app.include_router(encyclopedia_router)
    app.include_router(celestial_router)
    app.include_router(realtime_router)
    app.include_router(procedural_router)
    app.include_router(simulation_router)

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

    @app.get("/realtime")
    async def realtime_viewer():
        path = public / "realtime.html"
        if path.exists():
            return FileResponse(path)
        return {"service": "udm-earth-engine", "realtime": "public/realtime.html missing"}

    @app.get("/toroid")
    async def toroid_viewer():
        path = public / "toroid.html"
        if path.exists():
            return FileResponse(path)
        return {"service": "udm-earth-engine", "toroid": "public/toroid.html missing"}

    @app.get("/planar")
    @app.get("/planar/{rest:path}")
    @app.get("/simulate")
    @app.get("/globe")
    @app.get("/view")
    async def planar_simulation_viewer(rest: str = ""):
        planar_index = public / "planar" / "index.html"
        if planar_index.exists():
            if rest and (public / "planar" / rest).is_file():
                return FileResponse(public / "planar" / rest)
            return FileResponse(planar_index)
        legacy = public / "simulate.html"
        if legacy.exists():
            return FileResponse(legacy)
        return {"service": "udm-earth-engine", "planar": "run npm run build:planar"}

    return app


app = create_app()


def main() -> None:
    s = get_settings()
    uvicorn.run("earth.main:app", host=s.app_host, port=s.app_port, reload=s.app_env == "development")


if __name__ == "__main__":
    main()