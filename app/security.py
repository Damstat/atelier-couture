"""Hachage des mots de passe (RG21)."""
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()


def hacher_mot_de_passe(mot_de_passe: str) -> str:
    return _hasher.hash(mot_de_passe)


def verifier_mot_de_passe(mot_de_passe: str, mot_de_passe_hash: str) -> bool:
    try:
        return _hasher.verify(mot_de_passe_hash, mot_de_passe)
    except (VerificationError, InvalidHashError):
        return False
