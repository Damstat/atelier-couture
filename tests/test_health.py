from sqlalchemy.exc import OperationalError

from app.database import get_db
from app.main import app


def test_health_repond_ok_apres_avoir_verifie_la_base(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_health_503_si_la_base_ne_repond_pas(client):
    class BaseEnPanne:
        def execute(self, *args, **kwargs):
            raise OperationalError("SELECT 1", {}, Exception("connexion refusée"))

    app.dependency_overrides[get_db] = lambda: BaseEnPanne()
    r = client.get("/health")
    assert r.status_code == 503
    assert r.json() == {"detail": "La base de données ne répond pas."}
