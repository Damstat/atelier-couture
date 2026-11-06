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


def test_types_vetement_avant_remise_du_plus_eleve_au_plus_faible(client, headers, stats, donnees):
    r = get(client, headers, "types-vetement")
    assert r.status_code == 200
    assert r.json() == [
        {"type_vetement_id": donnees["boubou"], "nom": "Boubou", "quantite_vendue": 2, "chiffre_affaires": 60000},
        {"type_vetement_id": donnees["pantalon"], "nom": "Pantalon", "quantite_vendue": 2, "chiffre_affaires": 24000},
    ]


def test_types_vetement_commandes_annulees_exclues(client, headers, stats):
    debut = (DEBUT_MOIS - timedelta(days=90)).isoformat()
    r = get(client, headers, "types-vetement", date_debut=debut).json()
    # Boubou : 2 (c1) + 1 (c4) ; la commande annulée c3 n'est pas comptée
    assert [(t["nom"], t["quantite_vendue"], t["chiffre_affaires"]) for t in r] == [
        ("Boubou", 3, 90000), ("Pantalon", 3, 36000)]


def test_top_clients_de_la_periode(client, headers, stats, donnees):
    r = get(client, headers, "top-clients")
    assert r.status_code == 200
    assert r.json() == [
        {"client_id": donnees["fatou"], "client_nom": "Fatou Diop", "telephone": "771234567",
         "nb_commandes": 1, "chiffre_affaires": 70000, "solde_du": 50000},
        {"client_id": donnees["awa"], "client_nom": "Awa Ba", "telephone": "781112233",
         "nb_commandes": 1, "chiffre_affaires": 12000, "solde_du": 0},
    ]


def test_top_clients_limite_et_periode_large(client, headers, stats):
    debut = (DEBUT_MOIS - timedelta(days=90)).isoformat()
    r = get(client, headers, "top-clients", date_debut=debut, limite=1).json()
    # Fatou : c1 + c5 (c3 annulée exclue) = 82 000 ; Awa : c2 + c4 = 42 000
    assert len(r) == 1 and r[0]["client_nom"] == "Fatou Diop"
    assert r[0]["nb_commandes"] == 2 and r[0]["chiffre_affaires"] == 82000 and r[0]["solde_du"] == 62000
    assert get(client, headers, "top-clients", limite=0).status_code == 422
