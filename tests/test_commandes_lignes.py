import pytest

from tests.factories import URL_COMMANDES as URL
from tests.factories import corps_commande, creer_commande


@pytest.fixture()
def commande(client, headers, donnees):
    return creer_commande(client, headers["accueil"], corps_commande(donnees)).json()


def ajouter(client, h, cid, **ligne):
    return client.post(f"{URL}/{cid}/lignes", json=ligne, headers=h)


def test_ajouter_ligne_201_recalcule_le_total(client, headers, commande, donnees):
    r = ajouter(client, headers["accueil"], commande["id"], type_vetement_id=donnees["pantalon"], quantite=2)
    assert r.status_code == 201
    c = r.json()
    assert len(c["lignes"]) == 3
    assert c["lignes"][-1]["prix_unitaire"] == 12000 and c["lignes"][-1]["sous_total"] == 24000
    assert c["montant_total"] == 70000 + 24000


def test_ajouter_ligne_prestation_inactive_422(client, headers, commande, donnees):
    r = ajouter(client, headers["accueil"], commande["id"], type_vetement_id=donnees["retiree"])
    assert r.status_code == 422


def test_retirer_ligne_recalcule_le_total(client, headers, commande):
    pantalon = commande["lignes"][1]
    r = client.delete(f"{URL}/{commande['id']}/lignes/{pantalon['id']}", headers=headers["accueil"])
    assert r.status_code == 200
    assert len(r.json()["lignes"]) == 1 and r.json()["montant_total"] == 58000


def test_rg10_au_moins_une_ligne_409(client, headers, commande):
    l1, l2 = commande["lignes"]
    client.delete(f"{URL}/{commande['id']}/lignes/{l2['id']}", headers=headers["accueil"])
    r = client.delete(f"{URL}/{commande['id']}/lignes/{l1['id']}", headers=headers["accueil"])
    assert r.status_code == 409 and "au moins une prestation" in r.json()["detail"]


def test_rg7_retirer_une_ligne_sous_la_remise_422(client, headers, commande):
    client.patch(f"{URL}/{commande['id']}", json={"remise": 65000}, headers=headers["accueil"])
    boubous = commande["lignes"][0]
    r = client.delete(f"{URL}/{commande['id']}/lignes/{boubous['id']}", headers=headers["accueil"])
    assert r.status_code == 422 and "remise" in r.json()["detail"]


def test_rg10_lignes_figees_hors_en_attente_409(client, headers, commande, donnees):
    client.post(f"{URL}/{commande['id']}/statut", json={"statut": "en_coupe"}, headers=headers["tailleur"])
    r = ajouter(client, headers["accueil"], commande["id"], type_vetement_id=donnees["pantalon"])
    assert r.status_code == 409 and "en_attente" in r.json()["detail"]
    ligne = commande["lignes"][0]["id"]
    assert client.delete(f"{URL}/{commande['id']}/lignes/{ligne}", headers=headers["accueil"]).status_code == 409


def test_lignes_404_et_droits(client, headers, commande, donnees):
    h = headers["accueil"]
    assert client.delete(f"{URL}/{commande['id']}/lignes/9999", headers=h).status_code == 404
    assert ajouter(client, h, 9999, type_vetement_id=donnees["pantalon"]).status_code == 404
    assert ajouter(client, headers["tailleur"], commande["id"], type_vetement_id=donnees["pantalon"]).status_code == 403
    ligne = commande["lignes"][0]["id"]
    assert client.delete(f"{URL}/{commande['id']}/lignes/{ligne}", headers=headers["tailleur"]).status_code == 403
