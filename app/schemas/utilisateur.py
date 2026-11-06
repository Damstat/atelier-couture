from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import Role


class UtilisateurRead(BaseModel):
    """Profil public : jamais de mot de passe ni de hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    nom_complet: str
    role: Role
    actif: bool
    created_at: datetime
