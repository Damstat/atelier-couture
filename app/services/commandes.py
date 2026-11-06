"""Règles de gestion des commandes."""
from collections.abc import Iterable
from datetime import date, timedelta

from app.exceptions import Conflit, DonneesInvalides
from app.models import Commande
from app.models.enums import StatutCommande

STATUTS_FINAUX = {StatutCommande.livree, StatutCommande.annulee}


# ---------- Calculs (RG7, RG8) ----------

def sous_total_lignes(lignes: Iterable) -> int:
    """Somme des (quantité × prix unitaire)."""
    return sum(l.quantite * l.prix_unitaire for l in lignes)


def calculer_total(sous_total: int, remise: int) -> int:
    """RG7 : total = somme des prestations - remise ; la remise ne peut pas dépasser la somme."""
    if remise > sous_total:
        raise DonneesInvalides(
            f"La remise ({remise} FCFA) ne peut pas dépasser la somme des prestations ({sous_total} FCFA)."
        )
    return sous_total - remise


def verifier_total_couvre_paye(total: int, montant_paye: int) -> None:
    """RG7 : un changement ne peut jamais ramener le total sous le montant déjà payé."""
    if total < montant_paye:
        raise Conflit(
            f"Modification refusée : le nouveau total ({total} FCFA) serait inférieur "
            f"au montant déjà payé ({montant_paye} FCFA)."
        )


def recalculer_montants(commande: Commande) -> None:
    """Recalcule montant_total à partir des lignes et de la remise (RG7)."""
    total = calculer_total(sous_total_lignes(commande.lignes), commande.remise)
    verifier_total_couvre_paye(total, commande.montant_paye)
    commande.montant_total = total


def date_prevue_par_defaut(date_commande: date, delais_jours: Iterable[int]) -> date:
    """RG8 : date de commande + le plus long délai des prestations commandées."""
    return date_commande + timedelta(days=max(delais_jours, default=0))


def verifier_date_prevue(date_prevue: date, date_commande: date) -> None:
    """RG8 : la date prévue ne peut pas précéder la date de commande."""
    if date_prevue < date_commande:
        raise DonneesInvalides(
            f"La date de livraison prévue ({date_prevue.isoformat()}) ne peut pas précéder "
            f"la date de commande ({date_commande.isoformat()})."
        )


# ---------- Lecture ----------

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
