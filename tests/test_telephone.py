import pytest

from app.services.telephone import normaliser_telephone


@pytest.mark.parametrize("brut, attendu", [
    ("77 123 45 67", "771234567"),
    ("771234567", "771234567"),
    ("77.123.45.67", "771234567"),
    ("77-123-45-67", "771234567"),
    ("(77) 123 45 67", "771234567"),
    ("+221 77 123 45 67", "+221771234567"),
    ("123456", "123456"),
])
def test_rg1_normalisation(brut, attendu):
    assert normaliser_telephone(brut) == attendu


def test_rg1_meme_client_avec_deux_ecritures():
    assert normaliser_telephone("77 123 45 67") == normaliser_telephone("771234567")


@pytest.mark.parametrize("invalide", ["", "12345", "1" * 21, "77 12a 45 67", "++221771234567", "77+1234567", "   "])
def test_rg1_formes_invalides(invalide):
    with pytest.raises(ValueError):
        normaliser_telephone(invalide)
