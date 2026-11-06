from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.mesure import CHAMPS_MESURES

# RG2 : chaque mesure est facultative, strictement positive et ne dépasse pas 300 cm
Cm = Annotated[float | None, Field(default=None, gt=0, le=300, description="En centimètres")]


class _Valeurs(BaseModel):
    taille_cm: Cm = None
    tour_cou: Cm = None
    carrure_dos: Cm = None
    longueur_epaule: Cm = None
    tour_poitrine: Cm = None
    tour_taille: Cm = None
    tour_bassin: Cm = None
    longueur_manche: Cm = None
    tour_bras: Cm = None
    tour_poignet: Cm = None
    longueur_dos: Cm = None
    longueur_haut: Cm = None
    longueur_pantalon: Cm = None
    tour_cuisse: Cm = None
    tour_genou: Cm = None
    bas_pantalon: Cm = None
    entrejambe: Cm = None
    longueur_robe: Cm = None


MESSAGE_AUCUNE_MESURE = (
    "une prise de mesures doit contenir au moins une mesure "
    f"(parmi : {', '.join(CHAMPS_MESURES)})"
)


class MesureCreate(_Valeurs):
    date_prise: date | None = Field(default=None, description="Aujourd'hui par défaut")
    notes: str | None = None

    @model_validator(mode="after")
    def au_moins_une_mesure(self):
        # RG2
        if all(getattr(self, c) is None for c in CHAMPS_MESURES):
            raise ValueError(MESSAGE_AUCUNE_MESURE)
        return self


class MesureUpdate(_Valeurs):
    """PATCH : corrige une erreur de saisie ; envoyer null retire une mesure."""

    date_prise: date | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def date_non_vide(self):
        if "date_prise" in self.model_fields_set and self.date_prise is None:
            raise ValueError("date_prise ne peut pas être vide")
        return self


class MesureRead(_Valeurs):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    date_prise: date
    prise_par_id: int | None
    notes: str | None
