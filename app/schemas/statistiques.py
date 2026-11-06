from datetime import date
from typing import Literal

from pydantic import BaseModel

Granularite = Literal["jour", "mois"]


class TableauDeBord(BaseModel):
    chiffre_affaires_mois: int
    encaisse_mois: int
    nb_commandes_mois: int
    reste_a_encaisser: int
    commandes_par_statut: dict[str, int]
    nb_commandes_en_retard: int
    commandes_pretes_a_livrer: int
    livraisons_du_jour: int


class PeriodeCA(BaseModel):
    periode: str  # AAAA-MM-JJ ou AAAA-MM
    chiffre_affaires: int
    encaisse: int


class ChiffreAffaires(BaseModel):
    granularite: Granularite
    date_debut: date
    date_fin: date
    periodes: list[PeriodeCA]
    total_chiffre_affaires: int
    total_encaisse: int


class StatTypeVetement(BaseModel):
    type_vetement_id: int
    nom: str
    quantite_vendue: int
    chiffre_affaires: int


class TopClient(BaseModel):
    client_id: int
    client_nom: str
    telephone: str
    nb_commandes: int
    chiffre_affaires: int
    solde_du: int
