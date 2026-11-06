from datetime import date, timedelta

import pytest

from tests.factories import URL_COMMANDES as URL
from tests.factories import corps_commande, creer_commande


@pytest.fixture()
def commande(client, headers, donnees):
    return creer_commande(client, headers["accueil"], corps_commande(donnees)).json()  # total 70 000


def payer(client, h, cid, montant, mode="wave", **autres):
    return client.post(f"{URL}/{cid}/paiements", json={"montant": montant, "mode": mode, **autres}, headers=h)


def detail(client, h, cid):
    return client.get(f"{URL}/{cid}", headers=h).json()


def test_encaisser_un_acompte_201(client, headers, commande, utilisateurs):
    r = payer(client, headers["accueil"], commande["id"], 20000, reference="WAVE-123")
    assert r.status_code == 201
    p = r.json()
    assert p["montant"] == 20000 and p["mode"] == "wave" and p["reference"] == "WAVE-123"
    assert p["date_paiement"] == date.today().isoformat()
    assert p["enregistre_par_id"] == utilisateurs["accueil"].id
    c = detail(client, headers["accueil"], commande["id"])
    assert c["montant_paye"] == 20000 and c["solde"] == 50000


def test_encaisser_le_solde_exact(client, headers, commande):
    payer(client, headers["accueil"], commande["id"], 20000)
    assert payer(client, headers["accueil"], commande["id"], 50000, mode="especes").status_code == 201
    assert detail(client, headers["accueil"], commande["id"])["solde"] == 0


def test_rg16_paiement_superieur_au_solde_409(client, headers, commande):
    payer(client, headers["accueil"], commande["id"], 20000)
    r = payer(client, headers["accueil"], commande["id"], 50001)
    assert r.status_code == 409
    assert "50000 FCFA" in r.json()["detail"] and "solde restant" in r.json()["detail"]


def test_rg16_montant_strictement_positif_422(client, headers, commande):
    assert payer(client, headers["accueil"], commande["id"], 0).status_code == 422
    assert payer(client, headers["accueil"], commande["id"], -100).status_code == 422


def test_rg16_date_future_422_date_passee_acceptee(client, headers, commande):
    demain = (date.today() + timedelta(days=1)).isoformat()
    r = payer(client, headers["accueil"], commande["id"], 1000, date_paiement=demain)
    assert r.status_code == 422 and "futur" in r.json()["detail"]
    hier = (date.today() - timedelta(days=1)).isoformat()
    assert payer(client, headers["accueil"], commande["id"], 1000, date_paiement=hier).json()["date_paiement"] == hier


def test_rg16_commande_annulee_409(client, headers, commande):
    client.post(f"{URL}/{commande['id']}/statut", json={"statut": "annulee"}, headers=headers["accueil"])
    r = payer(client, headers["accueil"], commande["id"], 1000)
    assert r.status_code == 409 and "annulée" in r.json()["detail"]


def test_encaisser_mode_invalide_404_et_droits(client, headers, commande):
    assert payer(client, headers["accueil"], commande["id"], 1000, mode="bitcoin").status_code == 422
    assert payer(client, headers["accueil"], 9999, 1000).status_code == 404
    assert payer(client, headers["tailleur"], commande["id"], 1000).status_code == 403
    assert payer(client, headers["admin"], commande["id"], 1000).status_code == 201


def test_lister_paiements_dans_l_ordre_de_saisie(client, headers, commande):
    payer(client, headers["accueil"], commande["id"], 10000, mode="wave")
    payer(client, headers["accueil"], commande["id"], 5000, mode="especes",
          date_paiement=(date.today() - timedelta(days=3)).isoformat())
    r = client.get(f"{URL}/{commande['id']}/paiements", headers=headers["tailleur"])
    assert r.status_code == 200
    assert [(p["montant"], p["mode"]) for p in r.json()] == [(10000, "wave"), (5000, "especes")]
    assert client.get(f"{URL}/9999/paiements", headers=headers["tailleur"]).status_code == 404
