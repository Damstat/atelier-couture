"""Hachage des mots de passe (RG21) et jetons JWT (RG22)."""
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.config import settings

ALGORITHME = "HS256"

_hasher = PasswordHasher()


def hacher_mot_de_passe(mot_de_passe: str) -> str:
    return _hasher.hash(mot_de_passe)


def verifier_mot_de_passe(mot_de_passe: str, mot_de_passe_hash: str) -> bool:
    try:
        return _hasher.verify(mot_de_passe_hash, mot_de_passe)
    except (VerificationError, InvalidHashError):
        return False


def creer_jeton(utilisateur_id: int, expire_minutes: int | None = None) -> str:
    """Jeton JWT signé contenant l'identifiant de l'utilisateur et une expiration."""
    minutes = expire_minutes if expire_minutes is not None else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    maintenant = datetime.now(timezone.utc)
    charge = {
        "sub": str(utilisateur_id),
        "iat": maintenant,
        "exp": maintenant + timedelta(minutes=minutes),
    }
    return jwt.encode(charge, settings.SECRET_KEY, algorithm=ALGORITHME)


def lire_jeton(jeton: str) -> int | None:
    """Renvoie l'identifiant de l'utilisateur, ou None si le jeton est invalide ou expiré."""
    try:
        charge = jwt.decode(
            jeton, settings.SECRET_KEY, algorithms=[ALGORITHME],
            options={"require": ["exp", "sub"]},
        )
        return int(charge["sub"])
    except (jwt.PyJWTError, ValueError):
        return None
