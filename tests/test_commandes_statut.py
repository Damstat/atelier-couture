import pytest

from app.models import HistoriqueStatut
from tests.test_commandes import URL, corps_commande, creer, donnees  # noqa: F401  (fixture)


@pytest.fixture()
def cid(client, headers, donnees):  # noqa: F811
    return creer(client, headers["accueil"], corps_commande(donnees)).json()["id"]


def statut(client, h, cid, s, commentaire=None):
    corps = {"statut": s} if commentaire is None else {"statut": s, "commentaire": commentaire}
    return client.post(f"{URL}/{cid}/statut", json=corps, headers=h)


def test_tailleur_fait_avancer_la_production_avec_aller_retour(client, headers, cid, db):
    h = headers["tailleur"]
    for s in ["en_coupe", "en_couture", "essayage", "retouches", "essayage", "terminee"]:
        r = statut(client, h, cid, s)
        assert r.status_code == 200, r.text
        assert r.json()["statut"] == s
    # RG15 : création + 6 changements
    h = db.query(HistoriqueStatut).filter_by(commande_id=cid).order_by(HistoriqueStatut.id).all()
    assert [(x.ancien_statut and x.ancien_statut.value, x.nouveau_statut.value) for x in h] == [
        (None, "en_attente"), ("en_attente", "en_coupe"), ("en_coupe", "en_couture"),
        ("en_couture", "essayage"), ("essayage", "retouches"), ("retouches", "essayage"),
        ("essayage", "terminee")]


def test_transition_interdite_409_avec_statuts_possibles(client, headers, cid):
    r = statut(client, headers["accueil"], cid, "terminee")
    assert r.status_code == 409
    assert r.json()["detail"] == "Transition interdite : en_attente → terminee. Statuts possibles : annulee, en_coupe."


def test_rg13_meme_statut_et_livree_409(client, headers, cid):
    assert statut(client, headers["accueil"], cid, "en_attente").status_code == 409
    r = statut(client, headers["accueil"], cid, "livree")
    assert r.status_code == 409 and "confirmation de livraison" in r.json()["detail"]


def test_rg14_tailleur_ne_peut_pas_annuler_403(client, headers, cid):
    r = statut(client, headers["tailleur"], cid, "annulee")
    assert r.status_code == 403 and "tailleur" in r.json()["detail"]


def test_accueil_annule_sans_acompte(client, headers, cid, db, utilisateurs):
    r = statut(client, headers["accueil"], cid, "annulee")
    assert r.status_code == 200 and r.json()["statut"] == "annulee"
    dernier = db.query(HistoriqueStatut).filter_by(commande_id=cid).order_by(HistoriqueStatut.id.desc()).first()
    assert dernier.utilisateur_id == utilisateurs["accueil"].id


def test_rg14_annuler_avec_acompte_exige_un_commentaire_422(client, headers, cid, db):
    from app.models import Commande

    db.get(Commande, cid).montant_paye = 10000
    db.commit()
    r = statut(client, headers["accueil"], cid, "annulee")
    assert r.status_code == 422 and "10000 FCFA" in r.json()["detail"]
    assert statut(client, headers["accueil"], cid, "annulee", "   ").status_code == 422
    r = statut(client, headers["accueil"], cid, "annulee", "Remboursé en espèces")
    assert r.status_code == 200
    dernier = db.query(HistoriqueStatut).filter_by(commande_id=cid).order_by(HistoriqueStatut.id.desc()).first()
    assert dernier.commentaire == "Remboursé en espèces"


def test_rg12_commande_annulee_n_evolue_plus(client, headers, cid):
    statut(client, headers["accueil"], cid, "annulee")
    r = statut(client, headers["accueil"], cid, "en_coupe")
    assert r.status_code == 409 and "aucun (statut final)" in r.json()["detail"]


def test_statut_invalide_422_et_commande_inconnue_404(client, headers, cid):
    assert statut(client, headers["accueil"], cid, "perdue").status_code == 422
    assert statut(client, headers["accueil"], 9999, "en_coupe").status_code == 404
    assert client.post(f"{URL}/{cid}/statut", json={"statut": "en_coupe"}).status_code == 401
