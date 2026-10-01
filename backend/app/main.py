from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import api_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging("DEBUG" if settings.environment == "development" else "INFO")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings.ensure_dirs()
        yield

    app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {"name": settings.app_name, "version": __version__, "docs": "/docs"}

    return app


app = create_app()
