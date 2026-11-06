from app.security import hacher_mot_de_passe, verifier_mot_de_passe


def test_hash_argon2_jamais_en_clair():
    h = hacher_mot_de_passe("secret123")
    assert h != "secret123"
    assert h.startswith("$argon2")


def test_verification_mot_de_passe():
    h = hacher_mot_de_passe("secret123")
    assert verifier_mot_de_passe("secret123", h)
    assert not verifier_mot_de_passe("mauvais!!", h)
    assert not verifier_mot_de_passe("secret123", "hash-invalide")
