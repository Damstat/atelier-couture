"""Tests unitaires des règles de calcul (sans HTTP)."""
from datetime import date
from types import SimpleNamespace as L

import pytest

from app.exceptions import Conflit, DonneesInvalides
from app.models import Commande
from app.models.enums import StatutCommande
from app.services import commandes as svc


def test_rg7_total_somme_des_lignes_moins_remise():
    lignes = [L(quantite=2, prix_unitaire=30000), L(quantite=1, prix_unitaire=12000)]
    assert svc.sous_total_lignes(lignes) == 72000
    assert svc.calculer_total(72000, 2000) == 70000
    assert svc.calculer_total(72000, 72000) == 0


def test_rg7_remise_superieure_a_la_somme_422():
    with pytest.raises(DonneesInvalides, match="remise"):
        svc.calculer_total(10000, 10001)


def test_rg7_total_jamais_sous_le_paye_409():
    svc.verifier_total_couvre_paye(10000, 10000)
    with pytest.raises(Conflit, match="déjà payé"):
        svc.verifier_total_couvre_paye(9999, 10000)


def test_rg8_date_prevue_plus_long_delai():
    assert svc.date_prevue_par_defaut(date(2026, 3, 1), [4, 10, 7]) == date(2026, 3, 11)


def test_rg8_date_prevue_avant_la_commande_422():
    svc.verifier_date_prevue(date(2026, 3, 1), date(2026, 3, 1))
    with pytest.raises(DonneesInvalides, match="précéder"):
        svc.verifier_date_prevue(date(2026, 2, 28), date(2026, 3, 1))


@pytest.mark.parametrize("statut, attendu", [
    (StatutCommande.en_couture, True),
    (StatutCommande.terminee, True),
    (StatutCommande.livree, False),
    (StatutCommande.annulee, False),
])
def test_rg11_en_retard(statut, attendu):
    c = Commande(statut=statut, date_livraison_prevue=date(2026, 1, 1))
    assert svc.est_en_retard(c, aujourd_hui=date(2026, 1, 2)) is attendu
    assert svc.est_en_retard(c, aujourd_hui=date(2026, 1, 1)) is False
