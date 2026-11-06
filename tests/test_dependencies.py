import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.errors import installer_gestionnaires
from app.models.enums import Role
from app.security import creer_jeton


@pytest.fixture()
def mini(engine):
    app = FastAPI()
    installer_gestionnaires(app)
    Session = sessionmaker(bind=engine, autoflush=False)

    def _get_db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _get_db

    @app.get("/connecte")
    def connecte(u=Depends(get_current_user)):
        return {"email": u.email}

    @app.get("/tailleur")
    def tailleur(u=Depends(require_roles(Role.tailleur))):
        return {"ok": True}

    return TestClient(app)


def test_sans_jeton_401(mini):
    r = mini.get("/connecte")
    assert r.status_code == 401
    assert "jeton" in r.json()["detail"]


def test_jeton_invalide_401(mini):
    assert mini.get("/connecte", headers={"Authorization": "Bearer faux"}).status_code == 401


def test_jeton_valide(mini, headers):
    r = mini.get("/connecte", headers=headers["accueil"])
    assert r.status_code == 200
    assert r.json() == {"email": "accueil@atelier.sn"}


def test_compte_desactive_refuse_meme_avec_jeton_valide(mini, db, utilisateurs):
    jeton = creer_jeton(utilisateurs["tailleur"].id)
    utilisateurs["tailleur"].actif = False
    db.commit()
    r = mini.get("/connecte", headers={"Authorization": f"Bearer {jeton}"})
    assert r.status_code == 401
    assert "désactivé" in r.json()["detail"]


def test_role_insuffisant_403_et_admin_toujours_autorise(mini, headers):
    assert mini.get("/tailleur", headers=headers["tailleur"]).status_code == 200
    assert mini.get("/tailleur", headers=headers["admin"]).status_code == 200
    r = mini.get("/tailleur", headers=headers["accueil"])
    assert r.status_code == 403
    assert "accueil" in r.json()["detail"]
