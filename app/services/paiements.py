"""Paiements : acomptes et soldes (RG16, RG17)."""
from datetime import date

from sqlalchemy.orm import Session

from app.exceptions import Conflit, DonneesInvalides
from app.models import Commande, Paiement, Utilisateur
from app.models.enums import StatutCommande
from app.schemas.paiement import PaiementCreate
from app.services.commandes import obtenir_commande, solde


def recalculer_paye(commande: Commande) -> None:
    """RG7 : payé = somme des paiements."""
    commande.montant_paye = sum(p.montant for p in commande.paiements)


def encaisser(db: Session, commande_id: int, donnees: PaiementCreate, auteur: Utilisateur) -> Paiement:
    commande = obtenir_commande(db, commande_id)
    date_paiement = donnees.date_paiement or date.today()

    # RG16
    if commande.statut == StatutCommande.annulee:
        raise Conflit(f"La commande {commande.numero} est annulée : aucun paiement ne peut y être enregistré.")
    if date_paiement > date.today():
        raise DonneesInvalides(
            f"La date de paiement ({date_paiement.isoformat()}) ne peut pas être dans le futur."
        )
    reste = solde(commande)
    if donnees.montant > reste:
        raise Conflit(
            f"Le montant ({donnees.montant} FCFA) dépasse le solde restant de la commande "
            f"{commande.numero} ({reste} FCFA)."
        )

    paiement = Paiement(
        montant=donnees.montant, mode=donnees.mode, reference=donnees.reference,
        date_paiement=date_paiement, enregistre_par_id=auteur.id,
    )
    commande.paiements.append(paiement)
    recalculer_paye(commande)
    db.flush()
    return paiement


def paiements_commande(db: Session, commande_id: int) -> list[Paiement]:
    """Paiements dans l'ordre de saisie."""
    return list(obtenir_commande(db, commande_id).paiements)
