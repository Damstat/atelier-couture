from datetime import date, timedelta

import pytest

from app.models import Client, Mesure, TypeVetement

API = "/api/v1"
URL = f"{API}/commandes"


@pytest.fixture()
def donnees(db):
    """Une cliente avec deux prises de mesures, et un petit catalogue."""
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


def corps_commande(d, **autres):
    return {
        "client_id": d["fatou"],
        "lignes": [
            {"type_vetement_id": d["boubou"], "quantite": 2, "prix_unitaire": 30000},
            {"type_vetement_id": d["pantalon"]},
        ],
        "remise": 2000,
        **autres,
    }


def creer(client, h, corps):
    return client.post(URL, json=corps, headers=h)


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
