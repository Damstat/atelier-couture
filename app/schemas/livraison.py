from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ModeLivraison, StatutLivraison


class LivraisonPlanification(BaseModel):
    """PUT : planifie ou replanifie la livraison (remplace les valeurs existantes)."""

    mode: ModeLivraison
    date_prevue: date
    adresse: str | None = Field(default=None, max_length=255, description="Obligatoire pour « domicile » (RG18)")
    livreur: str | None = Field(default=None, max_length=150)
    notes: str | None = None


class LivraisonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    commande_id: int
    mode: ModeLivraison
    adresse: str | None
    livreur: str | None
    date_prevue: date
    date_effective: date | None
    statut: StatutLivraison
    notes: str | None
