from __future__ import annotations

import logging
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import JSON, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _sqlite_database_path(url: str) -> Path | None:
    if not url.startswith("sqlite:///"):
        return None
    raw = url.removeprefix("sqlite:///")
    if raw == ":memory:":
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def _patch_jsonb_for_sqlite() -> None:
    from app.db.models import Base

    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()


def _build_engine():
    url = settings.database_url
    kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}

    if url.startswith("sqlite"):
        _patch_jsonb_for_sqlite()
        db_path = _sqlite_database_path(url)
        if db_path is not None:
            db_path.parent.mkdir(parents=True, exist_ok=True)

    return create_engine(url, **kwargs)


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db() -> None:
    """Create tables automatically for local SQLite development."""
    if not settings.database_url.startswith("sqlite"):
        return
    from app.db.models import Base

    Base.metadata.create_all(bind=engine)
    logger.info("SQLite database ready at %s", settings.database_url)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except OperationalError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
