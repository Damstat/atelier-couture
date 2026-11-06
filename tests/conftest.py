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


MOT_DE_PASSE = "motdepasse123"
_HASH = None


def _hash_mot_de_passe() -> str:
    # Argon2 est volontairement lent : on ne hache qu'une fois pour toute la session
    global _HASH
    if _HASH is None:
        from app.security import hacher_mot_de_passe

        _HASH = hacher_mot_de_passe(MOT_DE_PASSE)
    return _HASH


@pytest.fixture()
def utilisateurs(db):
    """Un compte par rôle : {"admin": Utilisateur, "accueil": ..., "tailleur": ...}."""
    from app.models import Utilisateur
    from app.models.enums import Role

    comptes = {}
    for role, nom in [(Role.admin, "Patron"), (Role.accueil, "Awa Accueil"), (Role.tailleur, "Moussa Tailleur")]:
        u = Utilisateur(
            email=f"{role.value}@atelier.sn", nom_complet=nom,
            mot_de_passe_hash=_hash_mot_de_passe(), role=role, actif=True,
        )
        db.add(u)
        comptes[role.value] = u
    db.commit()
    return comptes


@pytest.fixture()
def headers(utilisateurs):
    """En-têtes d'authentification par rôle : headers["accueil"], etc."""
    from app.security import creer_jeton

    return {role: {"Authorization": f"Bearer {creer_jeton(u.id)}"} for role, u in utilisateurs.items()}


@pytest.fixture()
def donnees(db):
    """Une cliente avec deux prises de mesures, et un petit catalogue."""
    from datetime import date, timedelta

    from app.models import Client, Mesure, TypeVetement

    fatou = Client(nom="Diop", prenom="Fatou", telephone="771234567")
    awa = Client(nom="Ba", prenom="Awa", telephone="781112233")
    boubou = TypeVetement(nom="Boubou", prix_base=35000, delai_jours=10)
    pantalon = TypeVetement(nom="Pantalon", prix_base=12000, delai_jours=4)
    retiree = TypeVetement(nom="Ancienne", prix_base=1000, delai_jours=1, actif=False)
    db.add_all([fatou, awa, boubou, pantalon, retiree])
    db.flush()
    ancienne = Mesure(client_id=fatou.id, date_prise=date.today() - timedelta(days=60), tour_taille=80)
    recente = Mesure(client_id=fatou.id, date_prise=date.today() - timedelta(days=2), tour_taille=82)
    mesure_awa = Mesure(client_id=awa.id, tour_taille=70)
    db.add_all([ancienne, recente, mesure_awa])
    db.commit()
    return {
        "fatou": fatou.id, "awa": awa.id, "boubou": boubou.id, "pantalon": pantalon.id,
        "retiree": retiree.id, "mesure_ancienne": ancienne.id, "mesure_recente": recente.id,
        "mesure_awa": mesure_awa.id,
    }
