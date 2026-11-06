"""Livraisons (RG18 à RG20)."""
from sqlalchemy.orm import Session

from app.exceptions import DonneesInvalides
from app.models import Livraison
from app.models.enums import ModeLivraison, StatutLivraison
from app.schemas.livraison import LivraisonPlanification
from app.services.commandes import obtenir_commande, verifier_date_prevue, verifier_modifiable


def planifier(db: Session, commande_id: int, donnees: LivraisonPlanification) -> Livraison:
    commande = obtenir_commande(db, commande_id)
    verifier_modifiable(commande)  # 409 si livrée ou annulée

    adresse = (donnees.adresse or "").strip() or None
    # RG18 : une livraison à domicile exige une adresse
    if donnees.mode == ModeLivraison.domicile and adresse is None:
        raise DonneesInvalides("Une livraison à domicile exige une adresse.")
    verifier_date_prevue(donnees.date_prevue, commande.date_commande)

    # RG18 : replanifier modifie la livraison existante, sans en créer une seconde
    livraison = commande.livraison or Livraison(statut=StatutLivraison.planifiee)
    livraison.mode = donnees.mode
    livraison.date_prevue = donnees.date_prevue
    livraison.adresse = adresse
    livraison.livreur = donnees.livreur
    livraison.notes = donnees.notes
    commande.livraison = livraison

    # RG18 : planifier met à jour la date de livraison prévue de la commande
    commande.date_livraison_prevue = donnees.date_prevue
    db.flush()
    return livraison
