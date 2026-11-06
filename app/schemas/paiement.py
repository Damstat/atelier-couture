from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import ModePaiement


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
