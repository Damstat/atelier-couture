"""Création directe d'objets en base pour les tests (avant que les routes existent)."""
from datetime import date, timedelta

from app.models import Commande, Mesure
from app.models.enums import StatutCommande

URL_COMMANDES = "/api/v1/commandes"


def commande_en_base(db, client_id, numero="CMD-2026-00001", statut=StatutCommande.en_attente,
                     montant_total=10000, montant_paye=0, date_commande=None, date_prevue=None):
    d = date_commande or date.today()
    c = Commande(
        numero=numero, client_id=client_id, statut=statut, date_commande=d,
        date_livraison_prevue=date_prevue or d + timedelta(days=7), remise=0,
        montant_total=montant_total, montant_paye=montant_paye,
    )
    db.add(c)
    db.commit()
    return c


def mesure_en_base(db, client_id, **valeurs):
    m = Mesure(client_id=client_id, **(valeurs or {"tour_taille": 80}))
    db.add(m)
    db.commit()
    return m


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


def creer_commande(client, h, corps):
    return client.post(URL_COMMANDES, json=corps, headers=h)
