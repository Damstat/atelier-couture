from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import Role

MDP_MIN = 8  # RG21


def _nettoyer_nom(v: str | None) -> str | None:
    if v is None:
        return v
    v = " ".join(v.split())
    if not v:
        raise ValueError("ne peut pas être vide")
    return v


class UtilisateurCreate(BaseModel):
    email: EmailStr
    nom_complet: str = Field(min_length=1, max_length=150)
    mot_de_passe: str = Field(min_length=MDP_MIN, max_length=128)
    role: Role

    _nom = field_validator("nom_complet")(_nettoyer_nom)


class UtilisateurUpdate(BaseModel):
    """PATCH : seuls les champs envoyés sont modifiés."""

    nom_complet: str | None = Field(default=None, min_length=1, max_length=150)
    role: Role | None = None
    actif: bool | None = None
    mot_de_passe: str | None = Field(default=None, min_length=MDP_MIN, max_length=128)

    _nom = field_validator("nom_complet")(_nettoyer_nom)


class UtilisateurRead(BaseModel):
    """Profil public : jamais de mot de passe ni de hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    nom_complet: str
    role: Role
    actif: bool
    created_at: datetime
