import pytest
from pydantic import ValidationError

from app.schemas.mesure import MesureCreate


def test_rg2_au_moins_une_mesure():
    with pytest.raises(ValidationError, match="au moins une mesure"):
        MesureCreate(notes="rien")
    assert MesureCreate(tour_taille=80).tour_taille == 80


@pytest.mark.parametrize("valeur", [0, -5, 300.5, 1000])
def test_rg2_mesure_strictement_positive_et_au_plus_300(valeur):
    with pytest.raises(ValidationError):
        MesureCreate(tour_taille=valeur)


def test_rg2_bornes_acceptees():
    m = MesureCreate(tour_poignet=0.5, taille_cm=300)
    assert m.tour_poignet == 0.5 and m.taille_cm == 300
