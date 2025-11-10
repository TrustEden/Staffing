from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from . import models  # noqa: F401
from .database import Base, engine
from .routes import register_routes


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Healthcare Staffing Bridge API",
        version="0.1.0",
        debug=settings.debug,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def _on_startup() -> None:
        # Auto-create tables in development; rely on migrations for prod.
        if settings.app_env == "development":
            Base.metadata.create_all(bind=engine)

    register_routes(app)
    return app
