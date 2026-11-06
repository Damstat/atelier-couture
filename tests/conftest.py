"""Configuration commune des tests.

Les tests tournent sur SQLite en mémoire (toléré par l'énoncé pour les tests) :
ils ne dépendent ni du fichier .env ni d'un serveur PostgreSQL.
"""
import os

# Valeurs factices, définies AVANT d'importer l'application (app.config les lit).
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ["SECRET_KEY"] = "cle-de-test-uniquement-pour-pytest-0123456789"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (enregistre toutes les tables)
from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Comme PostgreSQL : respecter les clés étrangères
    @event.listens_for(eng, "connect")
    def _activer_fk(dbapi_connection, _record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    # Tests uniquement : en production le schéma vient de « alembic upgrade head »
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture()
def db(engine):
    session = sessionmaker(bind=engine, autoflush=False)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(engine):
    TestSession = sessionmaker(bind=engine, autoflush=False)

    def _get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
