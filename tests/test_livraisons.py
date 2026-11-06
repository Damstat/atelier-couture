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


def test_detail_livraison_et_404_si_aucune(client, headers, commande):
    r = client.get(f"{URL}/{commande['id']}/livraison", headers=headers["tailleur"])
    assert r.status_code == 404 and "Aucune livraison" in r.json()["detail"]
    planifier(client, headers["accueil"], commande["id"])
    r = client.get(f"{URL}/{commande['id']}/livraison", headers=headers["tailleur"])
    assert r.status_code == 200 and r.json()["adresse"] == "Médina, rue 6"


def terminer(client, headers, cid):
    for s in ["en_coupe", "en_couture", "terminee"]:
        client.post(f"{URL}/{cid}/statut", json={"statut": s}, headers=headers["tailleur"])


def payer(client, headers, cid, montant):
    client.post(f"{URL}/{cid}/paiements", json={"montant": montant, "mode": "wave"}, headers=headers["accueil"])


def confirmer(client, h, cid, corps=None):
    return client.post(f"{URL}/{cid}/livraison/confirmer", json=corps, headers=h)


def test_rg19_commande_non_terminee_409(client, headers, commande):
    payer(client, headers, commande["id"], 70000)
    r = confirmer(client, headers["accueil"], commande["id"])
    assert r.status_code == 409 and "terminee" in r.json()["detail"]


def test_rg19_solde_impaye_409_avec_le_montant(client, headers, commande):
    terminer(client, headers, commande["id"])
    payer(client, headers, commande["id"], 20000)
    r = confirmer(client, headers["accueil"], commande["id"])
    assert r.status_code == 409 and "50000 FCFA" in r.json()["detail"]


def test_rg20_confirmation_soldee_avec_livraison_planifiee(client, headers, commande):
    terminer(client, headers, commande["id"])
    planifier(client, headers["accueil"], commande["id"])
    payer(client, headers, commande["id"], 70000)
    r = confirmer(client, headers["accueil"], commande["id"])
    assert r.status_code == 200
    c = r.json()
    assert c["statut"] == "livree" and c["solde"] == 0
    assert c["date_livraison_reelle"] == date.today().isoformat()
    assert c["livraison"]["statut"] == "livree" and c["livraison"]["date_effective"] == date.today().isoformat()
    assert c["livraison"]["mode"] == "domicile"
    hist = client.get(f"{URL}/{commande['id']}/historique", headers=headers["accueil"]).json()
    assert hist[-1]["ancien_statut"] == "terminee" and hist[-1]["nouveau_statut"] == "livree"


def test_rg20_sans_planification_retrait_atelier_cree(client, headers, commande, db):
    from app.models import Livraison

    terminer(client, headers, commande["id"])
    payer(client, headers, commande["id"], 70000)
    r = confirmer(client, headers["accueil"], commande["id"], {"date_effective": date.today().isoformat()})
    assert r.status_code == 200
    assert r.json()["livraison"]["mode"] == "retrait_atelier"
    assert db.query(Livraison).count() == 1


def test_rg19_solde_impaye_autorise_mention_dans_l_historique(client, headers, commande):
    terminer(client, headers, commande["id"])
    payer(client, headers, commande["id"], 20000)
    r = confirmer(client, headers["accueil"], commande["id"], {"autoriser_solde_impaye": True})
    assert r.status_code == 200
    assert r.json()["statut"] == "livree" and r.json()["solde"] == 50000  # la dette reste visible
    hist = client.get(f"{URL}/{commande['id']}/historique", headers=headers["accueil"]).json()
    assert "50000 FCFA" in hist[-1]["commentaire"]


def test_confirmation_date_future_422_deja_livree_409_droits(client, headers, commande):
    terminer(client, headers, commande["id"])
    payer(client, headers, commande["id"], 70000)
    demain = (date.today() + timedelta(days=1)).isoformat()
    assert confirmer(client, headers["accueil"], commande["id"], {"date_effective": demain}).status_code == 422
    assert confirmer(client, headers["tailleur"], commande["id"]).status_code == 403
    assert confirmer(client, headers["accueil"], commande["id"]).status_code == 200
    assert confirmer(client, headers["accueil"], commande["id"]).status_code == 409
    assert planifier(client, headers["accueil"], commande["id"]).status_code == 409  # RG12
    assert confirmer(client, headers["accueil"], 9999).status_code == 404
