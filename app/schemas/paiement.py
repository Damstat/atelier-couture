from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ModePaiement


class PaiementCreate(BaseModel):
    montant: int = Field(gt=0, description="En FCFA, strictement positif (RG16)")
    mode: ModePaiement
    reference: str | None = Field(default=None, max_length=100)
    date_paiement: date | None = Field(default=None, description="Aujourd'hui par défaut ; jamais dans le futur")


class PaiementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    commande_id: int
    montant: int
    mode: ModePaiement
    reference: str | None
    date_paiement: date
    enregistre_par_id: int | None
    created_at: datetime
