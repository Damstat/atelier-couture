from datetime import date

from pydantic import BaseModel, Field

from app.models.enums import StatutCommande
from app.schemas.livraison import LivraisonRead
from app.schemas.paiement import PaiementRead


class LigneCreate(BaseModel):
    type_vetement_id: int
    quantite: int = Field(default=1, ge=1, le=1000)
    prix_unitaire: int | None = Field(
        default=None, ge=0, description="Prix négocié en FCFA ; prix de base du catalogue par défaut (RG6)"
    )
    description: str | None = None


class CommandeCreate(BaseModel):
    client_id: int
    mesure_id: int | None = Field(default=None, description="Dernières mesures du client par défaut (RG9)")
    lignes: list[LigneCreate] = Field(min_length=1)
    remise: int = Field(default=0, ge=0)
    date_livraison_prevue: date | None = Field(
        default=None, description="Date du jour + plus long délai des prestations par défaut (RG8)"
    )
    notes: str | None = None


class LigneRead(BaseModel):
    id: int
    type_vetement_id: int
    type_vetement_nom: str
    description: str | None
    quantite: int
    prix_unitaire: int
    sous_total: int


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


class CommandeDetail(CommandeResume):
    mesure_id: int | None
    notes: str | None
    cree_par_id: int | None
    lignes: list[LigneRead]
    paiements: list[PaiementRead]
    livraison: LivraisonRead | None
