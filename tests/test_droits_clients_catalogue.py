"""Droits par rôle (section 4) : lecture pour tous, suppression client et catalogue en écriture pour l'admin."""
import pytest

from app.models import Client, TypeVetement

API = "/api/v1"
TOUS = ["admin", "accueil", "tailleur"]


@pytest.fixture()
def ids(db):
    c = Client(nom="Diop", prenom="Fatou", telephone="771234567")
    t = TypeVetement(nom="Boubou", prix_base=35000, delai_jours=10)
    db.add_all([c, t])
    db.commit()
    return {"client": c.id, "prestation": t.id}


def _routes(ids):
    c, t = ids["client"], ids["prestation"]
    # (méthode, url, corps, rôles autorisés, code attendu si autorisé)
    return [
        ("post", f"{API}/clients", {"nom": "Ba", "prenom": "Ali", "telephone": "781112233"}, TOUS, 201),
        ("get", f"{API}/clients", None, TOUS, 200),
        ("get", f"{API}/clients/{c}", None, TOUS, 200),
        ("patch", f"{API}/clients/{c}", {"notes": "VIP"}, TOUS, 200),
        ("get", f"{API}/clients/{c}/commandes", None, TOUS, 200),
        ("get", f"{API}/clients/{c}/resume", None, TOUS, 200),
        ("get", f"{API}/catalogue", None, TOUS, 200),
        ("get", f"{API}/catalogue/{t}", None, TOUS, 200),
        ("post", f"{API}/catalogue", {"nom": "Robe", "prix_base": 30000, "delai_jours": 7}, ["admin"], 201),
        ("patch", f"{API}/catalogue/{t}", {"prix_base": 36000}, ["admin"], 200),
    ]


@pytest.mark.parametrize("role", TOUS)
def test_droits_par_role(client, headers, ids, role):
    for methode, url, corps, autorises, code in _routes(ids):
        if corps and methode == "post":
            corps = {**corps, "nom": f"{corps['nom']}-{role}"}
            if "telephone" in corps:
                corps["telephone"] = {"admin": "700000001", "accueil": "700000002", "tailleur": "700000003"}[role]
        r = client.request(methode, url, json=corps, headers=headers[role])
        attendu = code if role in autorises else 403
        assert r.status_code == attendu, (role, methode, url, r.text)


def test_suppression_client_admin_seulement(client, headers, ids):
    url = f"{API}/clients/{ids['client']}"
    assert client.delete(url, headers=headers["accueil"]).status_code == 403
    assert client.delete(url, headers=headers["tailleur"]).status_code == 403
    assert client.delete(url, headers=headers["admin"]).status_code == 204


def test_sans_jeton_401_partout(client, ids):
    for methode, url, corps, _, _ in _routes(ids):
        assert client.request(methode, url, json=corps).status_code == 401, (methode, url)
    assert client.delete(f"{API}/clients/{ids['client']}").status_code == 401
