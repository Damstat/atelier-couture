from datetime import date, timedelta

import pytest

from app.models import Client
from tests.factories import URL_COMMANDES as URL
from tests.factories import corps_commande, creer_commande as creer


def test_creer_commande_201_tout_est_calcule_par_le_serveur(client, headers, donnees, utilisateurs):
    r = creer(client, headers["accueil"], corps_commande(donnees))
    assert r.status_code == 201, r.text
    c = r.json()
    # RG5 : numéro CMD-AAAA-NNNNN
    assert c["numero"] == f"CMD-{date.today().year}-{c['id']:05d}"
    # RG6 : prix négocié sur la 1re ligne, prix du catalogue sur la 2e
    assert [(l["type_vetement_nom"], l["prix_unitaire"], l["sous_total"]) for l in c["lignes"]] == [
        ("Boubou", 30000, 60000), ("Pantalon", 12000, 12000)]
    # RG7 : total = 72 000 - 2 000
    assert c["montant_total"] == 70000 and c["montant_paye"] == 0 and c["solde"] == 70000
    # RG8 : aujourd'hui + plus long délai (10 jours)
    assert c["date_livraison_prevue"] == (date.today() + timedelta(days=10)).isoformat()
    # RG9 : dernières mesures du client par défaut
    assert c["mesure_id"] == donnees["mesure_recente"]
    assert c["statut"] == "en_attente" and c["en_retard"] is False
    assert c["client_nom"] == "Fatou Diop" and c["cree_par_id"] == utilisateurs["accueil"].id
    assert c["paiements"] == [] and c["livraison"] is None


def test_montants_envoyes_par_le_client_sont_ignores(client, headers, donnees):
    r = creer(client, headers["accueil"], corps_commande(donnees, montant_total=1, statut="terminee"))
    assert r.json()["montant_total"] == 70000 and r.json()["statut"] == "en_attente"


def test_rg15_creation_inscrit_la_premiere_ligne_d_historique(client, headers, donnees, db, utilisateurs):
    from app.models import HistoriqueStatut

    cid = creer(client, headers["accueil"], corps_commande(donnees)).json()["id"]
    h = db.query(HistoriqueStatut).filter_by(commande_id=cid).all()
    assert [(x.ancien_statut, x.nouveau_statut.value) for x in h] == [(None, "en_attente")]
    assert h[0].utilisateur_id == utilisateurs["accueil"].id


def test_numeros_successifs(client, headers, donnees):
    n1 = creer(client, headers["accueil"], corps_commande(donnees)).json()["numero"]
    n2 = creer(client, headers["accueil"], corps_commande(donnees)).json()["numero"]
    assert n1 != n2 and n1[-5:] < n2[-5:]


def test_date_prevue_et_mesure_fournies(client, headers, donnees):
    prevue = (date.today() + timedelta(days=30)).isoformat()
    r = creer(client, headers["accueil"], corps_commande(
        donnees, date_livraison_prevue=prevue, mesure_id=donnees["mesure_ancienne"]))
    assert r.json()["date_livraison_prevue"] == prevue
    assert r.json()["mesure_id"] == donnees["mesure_ancienne"]


def test_client_sans_mesures_commande_sans_mesure(client, headers, donnees, db):
    sans = Client(nom="Sow", prenom="Ali", telephone="701234500")
    db.add(sans)
    db.commit()
    r = creer(client, headers["accueil"], corps_commande(donnees, client_id=sans.id))
    assert r.status_code == 201 and r.json()["mesure_id"] is None


def test_rg6_prestation_inactive_422(client, headers, donnees):
    corps = corps_commande(donnees, lignes=[{"type_vetement_id": donnees["retiree"]}])
    r = creer(client, headers["accueil"], corps)
    assert r.status_code == 422 and "retirée du catalogue" in r.json()["detail"]


def test_rg7_remise_superieure_aux_prestations_422(client, headers, donnees):
    r = creer(client, headers["accueil"], corps_commande(donnees, remise=72001))
    assert r.status_code == 422 and "remise" in r.json()["detail"]


def test_rg8_date_prevue_avant_aujourd_hui_422(client, headers, donnees):
    hier = (date.today() - timedelta(days=1)).isoformat()
    r = creer(client, headers["accueil"], corps_commande(donnees, date_livraison_prevue=hier))
    assert r.status_code == 422 and "précéder" in r.json()["detail"]


def test_rg9_mesure_d_un_autre_client_422(client, headers, donnees):
    r = creer(client, headers["accueil"], corps_commande(donnees, mesure_id=donnees["mesure_awa"]))
    assert r.status_code == 422 and "n'appartient pas" in r.json()["detail"]


def test_commande_sans_ligne_ou_quantite_nulle_422(client, headers, donnees):
    assert creer(client, headers["accueil"], corps_commande(donnees, lignes=[])).status_code == 422
    lignes = [{"type_vetement_id": donnees["boubou"], "quantite": 0}]
    assert creer(client, headers["accueil"], corps_commande(donnees, lignes=lignes)).status_code == 422


def test_references_inconnues_404(client, headers, donnees):
    assert creer(client, headers["accueil"], corps_commande(donnees, client_id=9999)).status_code == 404
    lignes = [{"type_vetement_id": 9999}]
    assert creer(client, headers["accueil"], corps_commande(donnees, lignes=lignes)).status_code == 404
    assert creer(client, headers["accueil"], corps_commande(donnees, mesure_id=9999)).status_code == 404


def test_creer_commande_droits(client, headers, donnees):
    assert creer(client, headers["tailleur"], corps_commande(donnees)).status_code == 403
    assert creer(client, headers["admin"], corps_commande(donnees)).status_code == 201
    assert client.post(URL, json=corps_commande(donnees)).status_code == 401


@pytest.fixture()
def plusieurs(db, donnees):
    """4 commandes variées, créées directement en base."""
    from app.models.enums import StatutCommande as S
    from tests.factories import commande_en_base

    il_y_a_30j = date.today() - timedelta(days=30)
    commande_en_base(db, donnees["fatou"], "CMD-2026-00001", S.en_couture, date_commande=il_y_a_30j)  # en retard
    commande_en_base(db, donnees["fatou"], "CMD-2026-00002", S.livree, date_commande=il_y_a_30j)
    commande_en_base(db, donnees["awa"], "CMD-2026-00003", S.en_attente)
    commande_en_base(db, donnees["fatou"], "CMD-2026-00004", S.annulee, montant_total=5000, montant_paye=1000)


def numeros(r):
    return [c["numero"] for c in r.json()["items"]]


def test_lister_commandes_plus_recente_d_abord_avec_client_nom_solde_retard(client, headers, plusieurs):
    r = client.get(URL, headers=headers["tailleur"])
    assert r.status_code == 200 and r.json()["total"] == 4
    assert numeros(r) == ["CMD-2026-00004", "CMD-2026-00003", "CMD-2026-00002", "CMD-2026-00001"]
    premiere = r.json()["items"][0]
    assert premiere["client_nom"] == "Fatou Diop" and premiere["solde"] == 4000
    assert {c["numero"]: c["en_retard"] for c in r.json()["items"]}["CMD-2026-00001"] is True


@pytest.mark.parametrize("params, attendus", [
    ({"statut": "livree"}, ["CMD-2026-00002"]),
    ({"en_retard": "true"}, ["CMD-2026-00001"]),
    ({"en_retard": "false"}, ["CMD-2026-00004", "CMD-2026-00003", "CMD-2026-00002"]),
    ({"numero": "00003"}, ["CMD-2026-00003"]),
    ({"date_max": (date.today() - timedelta(days=1)).isoformat()}, ["CMD-2026-00002", "CMD-2026-00001"]),
    ({"date_min": date.today().isoformat()}, ["CMD-2026-00004", "CMD-2026-00003"]),
])
def test_filtres_des_commandes(client, headers, plusieurs, params, attendus):
    assert numeros(client.get(URL, params=params, headers=headers["accueil"])) == attendus


def test_filtre_client_et_pagination(client, headers, plusieurs, donnees):
    r = client.get(URL, params={"client_id": donnees["awa"]}, headers=headers["accueil"])
    assert numeros(r) == ["CMD-2026-00003"]
    r = client.get(URL, params={"limit": 2, "offset": 2}, headers=headers["accueil"])
    assert r.json()["total"] == 4 and numeros(r) == ["CMD-2026-00002", "CMD-2026-00001"]


def test_filtres_invalides_422(client, headers, plusieurs):
    h = headers["accueil"]
    assert client.get(URL, params={"statut": "perdue"}, headers=h).status_code == 422
    r = client.get(URL, params={"date_min": "2026-05-01", "date_max": "2026-04-01"}, headers=h)
    assert r.status_code == 422 and "date_min" in r.json()["detail"]


def test_detail_commande_avec_lignes_paiements_livraison(client, headers, donnees, db):
    from app.models import Livraison, Paiement
    from app.models.enums import ModeLivraison, ModePaiement

    cid = creer(client, headers["accueil"], corps_commande(donnees)).json()["id"]
    db.add(Paiement(commande_id=cid, montant=10000, mode=ModePaiement.wave))
    db.add(Livraison(commande_id=cid, mode=ModeLivraison.domicile, adresse="Médina", date_prevue=date.today()))
    db.commit()

    r = client.get(f"{URL}/{cid}", headers=headers["tailleur"])
    assert r.status_code == 200
    c = r.json()
    assert len(c["lignes"]) == 2 and c["lignes"][0]["type_vetement_nom"] == "Boubou"
    assert [p["mode"] for p in c["paiements"]] == ["wave"]
    assert c["livraison"]["adresse"] == "Médina"
    assert "solde" in c and "en_retard" in c


def test_detail_commande_404(client, headers):
    r = client.get(f"{URL}/9999", headers=headers["tailleur"])
    assert r.status_code == 404 and r.json() == {"detail": "Commande 9999 introuvable."}


@pytest.fixture()
def commande(client, headers, donnees):
    return creer(client, headers["accueil"], corps_commande(donnees)).json()


def patch(client, h, cid, **corps):
    return client.patch(f"{URL}/{cid}", json=corps, headers=h)


def test_modifier_remise_recalcule_le_total(client, headers, commande):
    r = patch(client, headers["accueil"], commande["id"], remise=12000)
    assert r.status_code == 200
    assert r.json()["montant_total"] == 60000 and r.json()["solde"] == 60000


def test_modifier_date_notes_et_mesure(client, headers, commande, donnees):
    prevue = (date.today() + timedelta(days=20)).isoformat()
    r = patch(client, headers["accueil"], commande["id"], date_livraison_prevue=prevue, notes="urgent",
              mesure_id=donnees["mesure_ancienne"])
    assert r.status_code == 200
    c = r.json()
    assert c["date_livraison_prevue"] == prevue and c["notes"] == "urgent"
    assert c["mesure_id"] == donnees["mesure_ancienne"]
    assert c["remise"] == 2000  # inchangé


def test_modifier_commande_regles_422(client, headers, commande, donnees):
    h, cid = headers["accueil"], commande["id"]
    assert patch(client, h, cid, remise=72001).status_code == 422                       # RG7
    hier = (date.today() - timedelta(days=1)).isoformat()
    assert patch(client, h, cid, date_livraison_prevue=hier).status_code == 422          # RG8
    assert patch(client, h, cid, mesure_id=donnees["mesure_awa"]).status_code == 422     # RG9
    assert patch(client, h, cid, remise=None).status_code == 422


def test_rg7_remise_ne_peut_pas_ramener_le_total_sous_le_paye_409(client, headers, commande, db):
    from app.models import Commande

    db.get(Commande, commande["id"]).montant_paye = 65000
    db.commit()
    r = patch(client, headers["accueil"], commande["id"], remise=10000)
    assert r.status_code == 409 and "déjà payé" in r.json()["detail"]


def test_rg12_commande_annulee_non_modifiable_409(client, headers, commande):
    client.post(f"{URL}/{commande['id']}/statut", json={"statut": "annulee"}, headers=headers["accueil"])
    r = patch(client, headers["accueil"], commande["id"], notes="x")
    assert r.status_code == 409 and "plus modifiable" in r.json()["detail"]


def test_modifier_commande_droits_et_404(client, headers, commande):
    assert patch(client, headers["tailleur"], commande["id"], notes="x").status_code == 403
    assert patch(client, headers["accueil"], 9999, notes="x").status_code == 404
