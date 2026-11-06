from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _nom(v: str | None) -> str | None:
    if v is None:
        return v
    v = " ".join(v.split())
    if not v:
        raise ValueError("ne peut pas être vide")
    return v


class TypeVetementCreate(BaseModel):
    nom: str = Field(min_length=1, max_length=100)
    description: str | None = None
    prix_base: int = Field(gt=0, description="Prix en FCFA")
    delai_jours: int = Field(ge=0, le=365, description="Délai de confection en jours")

    _nom = field_validator("nom")(_nom)


class TypeVetementUpdate(BaseModel):
    """PATCH : seuls les champs envoyés sont modifiés. actif=false retire la prestation."""

    nom: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    prix_base: int | None = Field(default=None, gt=0)
    delai_jours: int | None = Field(default=None, ge=0, le=365)
    actif: bool | None = None

    _nom = field_validator("nom")(_nom)

    @model_validator(mode="after")
    def pas_de_null(self):
        nuls = [c for c in ("nom", "prix_base", "delai_jours", "actif")
                if c in self.model_fields_set and getattr(self, c) is None]
        if nuls:
            raise ValueError(f"ces champs ne peuvent pas être vides : {', '.join(nuls)}")
        return self


class TypeVetementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    description: str | None
    prix_base: int
    delai_jours: int
    actif: bool
