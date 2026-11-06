from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.enums import Genre
from app.schemas.commande import CommandeResume
from app.services.telephone import normaliser_telephone


def _texte_obligatoire(v: str | None) -> str | None:
    if v is None:
        return v
    v = " ".join(v.split())
    if not v:
        raise ValueError("ne peut pas être vide")
    return v


def _telephone(v: str | None) -> str | None:
    return None if v is None else normaliser_telephone(v)


class ClientCreate(BaseModel):
    nom: str = Field(min_length=1, max_length=100)
    prenom: str = Field(min_length=1, max_length=100)
    telephone: str = Field(max_length=40)
    email: EmailStr | None = None
    adresse: str | None = Field(default=None, max_length=255)
    genre: Genre | None = None
    notes: str | None = None

    _textes = field_validator("nom", "prenom")(_texte_obligatoire)
    _tel = field_validator("telephone")(_telephone)


class ClientUpdate(BaseModel):
    """PATCH : seuls les champs envoyés sont modifiés ; nom, prénom et téléphone ne peuvent pas être vidés."""

    nom: str | None = Field(default=None, min_length=1, max_length=100)
    prenom: str | None = Field(default=None, min_length=1, max_length=100)
    telephone: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = None
    adresse: str | None = Field(default=None, max_length=255)
    genre: Genre | None = None
    notes: str | None = None

    _textes = field_validator("nom", "prenom")(_texte_obligatoire)
    _tel = field_validator("telephone")(_telephone)

    @model_validator(mode="after")
    def obligatoires_non_vides(self):
        vides = [c for c in ("nom", "prenom", "telephone") if c in self.model_fields_set and getattr(self, c) is None]
        if vides:
            raise ValueError(f"ces champs ne peuvent pas être vidés : {', '.join(vides)}")
        return self


class ClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    prenom: str
    telephone: str
    email: str | None
    adresse: str | None
    genre: Genre | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ClientResume(BaseModel):
    """Synthèse d'un client (commandes annulées exclues)."""

    client_id: int
    nb_commandes: int
    chiffre_affaires: int
    total_paye: int
    solde_du: int
    derniere_commande: CommandeResume | None
    a_des_mesures: bool
