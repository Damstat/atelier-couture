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


def test_jeton_jwt_aller_retour():
    from app.security import creer_jeton, lire_jeton

    assert lire_jeton(creer_jeton(42)) == 42


def test_jeton_expire_refuse():
    from app.security import creer_jeton, lire_jeton

    assert lire_jeton(creer_jeton(42, expire_minutes=-1)) is None


def test_jeton_falsifie_refuse():
    import jwt

    from app.security import ALGORITHME, lire_jeton

    faux = jwt.encode({"sub": "1", "exp": 9999999999}, "autre-cle-secrete-de-test-xxxxxxxxxx", algorithm=ALGORITHME)
    assert lire_jeton(faux) is None
    assert lire_jeton("pas-un-jeton") is None
