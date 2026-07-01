"""Shared pytest fixtures."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.adapters.interfaces import RawLead
from app.db.models import Base
from app.db.session import get_db
from app.main import create_app


@pytest.fixture
def db_session():
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy import JSON

    # SQLite tests: JSONB columns need a stand-in type
    for table in Base.metadata.tables.values():
        for col in table.columns:
            if isinstance(col.type, JSONB):
                col.type = JSON()

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    app = create_app()

    def _override_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_raw_lead() -> RawLead:
    return RawLead(
        state="TX",
        county="Harris",
        source_module="tx.harris.tax_sale",
        property_address="123 Main St HOUSTON TX 77002",
        city="Houston",
        zip_code="77002",
        parcel_id="TEST123",
        distress_signals=["tax_delinquent"],
        raw_data={"minimum_bid": 1000.0},
    )
