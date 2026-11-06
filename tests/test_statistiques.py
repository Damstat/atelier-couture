"""Statistiques administrateur (routes 39 à 43)."""
from datetime import date, timedelta

import pytest

from app.models import LigneCommande, Livraison, Paiement
from app.models.enums import ModeLivraison, ModePaiement
from app.models.enums import StatutCommande as S
from tests.factories import commande_en_base

URL = "/api/v1/statistiques"
AUJOURD_HUI = date.today()
DEBUT_MOIS = AUJOURD_HUI.replace(day=1)
MOIS_DERNIER = DEBUT_MOIS - timedelta(days=1)


@pytest.fixture()
def stats(db, donnees):
    """5 commandes : 2 ce mois-ci, 3 le mois dernier (dont 1 annulée)."""
    f, a, boubou, pantalon = donnees["fatou"], donnees["awa"], donnees["boubou"], donnees["pantalon"]

    def commande(numero, client, statut, total, paye, jour, lignes, prevue=None):
        c = commande_en_base(db, client, numero, statut, montant_total=total, montant_paye=paye,
                             date_commande=jour, date_prevue=prevue)
        for type_id, q, pu in lignes:
            db.add(LigneCommande(commande_id=c.id, type_vetement_id=type_id, quantite=q, prix_unitaire=pu))
        if paye:
            db.add(Paiement(commande_id=c.id, montant=paye, mode=ModePaiement.wave, date_paiement=jour))
        db.commit()
        return c

    c1 = commande("CMD-1", f, S.en_couture, 70000, 20000, AUJOURD_HUI, [(boubou, 2, 30000), (pantalon, 1, 12000)])
    c2 = commande("CMD-2", a, S.terminee, 12000, 12000, AUJOURD_HUI, [(pantalon, 1, 12000)])
    commande("CMD-3", f, S.annulee, 35000, 0, MOIS_DERNIER, [(boubou, 1, 35000)])
    commande("CMD-4", a, S.livree, 30000, 30000, MOIS_DERNIER, [(boubou, 1, 30000)])
    c5 = commande("CMD-5", f, S.en_coupe, 12000, 0, MOIS_DERNIER, [(pantalon, 1, 12000)],
                  prevue=AUJOURD_HUI - timedelta(days=1))  # en retard
    db.add(Livraison(commande_id=c2.id, mode=ModeLivraison.retrait_atelier, date_prevue=AUJOURD_HUI))
    db.commit()
    return {"c1": c1.id, "c5": c5.id}


def get(client, headers, chemin, **params):
    return client.get(f"{URL}/{chemin}", params=params, headers=headers["admin"])


def test_tableau_de_bord(client, headers, stats):
    r = get(client, headers, "tableau-de-bord")
    assert r.status_code == 200
    t = r.json()
    assert t["chiffre_affaires_mois"] == 82000       # c1 + c2
    assert t["encaisse_mois"] == 32000               # paiements datés de ce mois
    assert t["nb_commandes_mois"] == 2
    assert t["reste_a_encaisser"] == 62000           # 50 000 (c1) + 12 000 (c5) ; annulée exclue
    assert t["commandes_par_statut"] == {
        "en_attente": 0, "en_coupe": 1, "en_couture": 1, "essayage": 0, "retouches": 0,
        "terminee": 1, "livree": 1, "annulee": 1,
    }
    assert t["nb_commandes_en_retard"] == 1
    assert t["commandes_pretes_a_livrer"] == 1
    assert t["livraisons_du_jour"] == 1


def test_tableau_de_bord_vide(client, headers):
    t = get(client, headers, "tableau-de-bord").json()
    assert t["chiffre_affaires_mois"] == 0 and t["reste_a_encaisser"] == 0
    assert set(t["commandes_par_statut"].values()) == {0} and len(t["commandes_par_statut"]) == 8


@pytest.mark.parametrize("role", ["accueil", "tailleur"])
def test_statistiques_reservees_a_l_admin(client, headers, role):
    r = client.get(f"{URL}/tableau-de-bord", headers=headers[role])
    assert r.status_code == 403
    assert client.get(f"{URL}/tableau-de-bord").status_code == 401


def test_chiffre_affaires_par_jour_periode_par_defaut(client, headers, stats):
    r = get(client, headers, "chiffre-affaires")
    assert r.status_code == 200
    ca = r.json()
    assert ca["date_debut"] == DEBUT_MOIS.isoformat() and ca["date_fin"] == AUJOURD_HUI.isoformat()
    assert ca["periodes"] == [{"periode": AUJOURD_HUI.isoformat(), "chiffre_affaires": 82000, "encaisse": 32000}]


def test_chiffre_affaires_par_mois_seules_les_periodes_actives(client, headers, stats):
    debut = (DEBUT_MOIS - timedelta(days=90)).isoformat()
    ca = get(client, headers, "chiffre-affaires", granularite="mois", date_debut=debut).json()
    assert ca["periodes"] == [
        {"periode": MOIS_DERNIER.strftime("%Y-%m"), "chiffre_affaires": 42000, "encaisse": 30000},
        {"periode": AUJOURD_HUI.strftime("%Y-%m"), "chiffre_affaires": 82000, "encaisse": 32000},
    ]
    assert ca["total_chiffre_affaires"] == 124000 and ca["total_encaisse"] == 62000


def test_chiffre_affaires_parametres_invalides_422(client, headers):
    r = get(client, headers, "chiffre-affaires", date_debut="2026-05-01", date_fin="2026-04-01")
    assert r.status_code == 422 and "date_debut" in r.json()["detail"]
    assert get(client, headers, "chiffre-affaires", granularite="annee").status_code == 422
