from datetime import date

from pydantic import BaseModel

from app.models.enums import StatutCommande


class CommandeResume(BaseModel):
    """Élément d'une liste de commandes."""

    id: int
    numero: str
    client_id: int
    client_nom: str
    statut: StatutCommande
    date_commande: date
    date_livraison_prevue: date
    date_livraison_reelle: date | None
    remise: int
    montant_total: int
    montant_paye: int
    solde: int
    en_retard: bool
