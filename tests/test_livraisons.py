from datetime import date, timedelta

import pytest

from tests.factories import URL_COMMANDES as URL
from tests.factories import corps_commande, creer_commande

DANS_5J = (date.today() + timedelta(days=5)).isoformat()


@pytest.fixture()
def commande(client, headers, donnees):
    return creer_commande(client, headers["accueil"], corps_commande(donnees)).json()  # total 70 000


def planifier(client, h, cid, **corps):
    return client.put(f"{URL}/{cid}/livraison", json={"mode": "domicile", "date_prevue": DANS_5J,
                                                       "adresse": "Médina, rue 6", **corps}, headers=h)


def test_planifier_livraison_met_a_jour_la_date_prevue(client, headers, commande):
    r = planifier(client, headers["accueil"], commande["id"], livreur="Ibou")
    assert r.status_code == 200
    l = r.json()
    assert l["mode"] == "domicile" and l["statut"] == "planifiee" and l["livreur"] == "Ibou"
    c = client.get(f"{URL}/{commande['id']}", headers=headers["accueil"]).json()
    assert c["date_livraison_prevue"] == DANS_5J  # RG18
    assert c["livraison"]["id"] == l["id"]


def test_rg18_domicile_sans_adresse_422(client, headers, commande):
    r = planifier(client, headers["accueil"], commande["id"], adresse="  ")
    assert r.status_code == 422 and "adresse" in r.json()["detail"]
    r = planifier(client, headers["accueil"], commande["id"], mode="retrait_atelier", adresse=None)
    assert r.status_code == 200


def test_rg18_replanifier_modifie_la_livraison_existante(client, headers, commande, db):
    from app.models import Livraison

    premiere = planifier(client, headers["accueil"], commande["id"]).json()
    dans_8j = (date.today() + timedelta(days=8)).isoformat()
    r = planifier(client, headers["accueil"], commande["id"], mode="retrait_atelier", adresse=None, date_prevue=dans_8j)
    assert r.json()["id"] == premiere["id"] and r.json()["mode"] == "retrait_atelier"
    assert db.query(Livraison).count() == 1


def test_planifier_date_avant_la_commande_422(client, headers, commande):
    hier = (date.today() - timedelta(days=1)).isoformat()
    assert planifier(client, headers["accueil"], commande["id"], date_prevue=hier).status_code == 422


def test_planifier_commande_annulee_409(client, headers, commande):
    client.post(f"{URL}/{commande['id']}/statut", json={"statut": "annulee"}, headers=headers["accueil"])
    r = planifier(client, headers["accueil"], commande["id"])
    assert r.status_code == 409 and "plus modifiable" in r.json()["detail"]


def test_planifier_droits_et_404(client, headers, commande):
    assert planifier(client, headers["tailleur"], commande["id"]).status_code == 403
    assert planifier(client, headers["accueil"], 9999).status_code == 404
