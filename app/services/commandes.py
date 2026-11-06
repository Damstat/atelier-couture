"""Règles de calcul sur les commandes."""
from datetime import date

from app.models import Commande
from app.models.enums import StatutCommande

STATUTS_FINAUX = {StatutCommande.livree, StatutCommande.annulee}


def solde(commande: Commande) -> int:
    """RG7 : solde = total - payé."""
    return commande.montant_total - commande.montant_paye


def est_en_retard(commande: Commande, aujourd_hui: date | None = None) -> bool:
    """RG11 : date prévue dépassée et commande ni livrée ni annulée."""
    aujourd_hui = aujourd_hui or date.today()
    return commande.statut not in STATUTS_FINAUX and commande.date_livraison_prevue < aujourd_hui


def nom_client(commande: Commande) -> str:
    return f"{commande.client.prenom} {commande.client.nom}"


def vers_resume(commande: Commande) -> dict:
    """Données d'une commande en liste (avec client_nom, solde, en_retard)."""
    return {
        "id": commande.id,
        "numero": commande.numero,
        "client_id": commande.client_id,
        "client_nom": nom_client(commande),
        "statut": commande.statut,
        "date_commande": commande.date_commande,
        "date_livraison_prevue": commande.date_livraison_prevue,
        "date_livraison_reelle": commande.date_livraison_reelle,
        "remise": commande.remise,
        "montant_total": commande.montant_total,
        "montant_paye": commande.montant_paye,
        "solde": solde(commande),
        "en_retard": est_en_retard(commande),
    }
