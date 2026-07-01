from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy.exc import OperationalError

from app.api.routes import router
from app.config import get_settings
from app.core.exceptions import (
    AppError,
    app_error_handler,
    database_error_handler,
    unhandled_error_handler,
)
from app.core.logging import setup_logging
from app.db.session import init_db
from app.middleware.request_id import RequestIdMiddleware
from app.middleware.security import SecurityHeadersMiddleware

DASHBOARD_DIST = Path(__file__).resolve().parents[2] / "dashboard" / "dist"
SPA_ROUTES = ("/", "/leads", "/sources", "/approval", "/settings")


def _rate_limit_key(request):
    settings = get_settings()
    if settings.api_key and request.headers.get("X-API-Key"):
        return request.headers.get("X-API-Key")
    return get_remote_address(request)


limiter = Limiter(key_func=_rate_limit_key, default_limits=["120/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    init_db()
    from app.email.scheduler import start_email_scheduler, stop_email_scheduler

    start_email_scheduler()
    yield
    stop_email_scheduler()


def _mount_dashboard(app: FastAPI) -> bool:
    index = DASHBOARD_DIST / "index.html"
    if not index.is_file():
        return False

    assets_dir = DASHBOARD_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="dashboard-assets")

    favicon = DASHBOARD_DIST / "favicon.svg"
    if favicon.is_file():

        @app.get("/favicon.svg", include_in_schema=False)
        def _favicon():
            return FileResponse(favicon)

    def _spa():
        return FileResponse(index)

    for route in SPA_ROUTES:
        app.add_api_route(route, _spa, methods=["GET"], include_in_schema=False)
    return True


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging()

    app = FastAPI(
        title="TX/FL Lead-Gen System",
        description="Distressed property lead generation and outreach (TX + FL only)",
        version="0.3.0",
        lifespan=lifespan,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(OperationalError, database_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)

    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix="/api")

    if not _mount_dashboard(app):

        @app.get("/")
        def root():
            return {
                "app": "TX/FL Lead-Gen System",
                "phase": 5,
                "version": "0.5.0",
                "docs": "/docs",
                "health": "/api/health",
                "dashboard_dev": "cd dashboard && npm run dev  →  http://localhost:5173",
                "require_human_approval": settings.require_human_approval,
            }

    return app


app = create_app()
