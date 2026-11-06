"""Dépendances FastAPI communes : utilisateur connecté, rôles, pagination."""
from collections.abc import Callable

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Utilisateur
from app.models.enums import Role
from app.schemas.common import LIMIT_DEFAUT, LIMIT_MAX
from app.security import lire_jeton

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

MESSAGE_401 = "Authentification requise : jeton absent, invalide ou expiré. Connectez-vous via /api/v1/auth/login."


def _non_authentifie(message: str = MESSAGE_401) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    jeton: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Utilisateur:
    if not jeton:
        raise _non_authentifie()
    utilisateur_id = lire_jeton(jeton)
    if utilisateur_id is None:
        raise _non_authentifie()
    utilisateur = db.get(Utilisateur, utilisateur_id)
    if utilisateur is None:
        raise _non_authentifie()
    # RG22 : un compte désactivé est refusé immédiatement, même avec un jeton valide
    if not utilisateur.actif:
        raise _non_authentifie("Ce compte est désactivé. Contactez l'administrateur.")
    return utilisateur


def require_roles(*roles: Role) -> Callable[..., Utilisateur]:
    """Autorise les rôles donnés. L'administrateur est toujours autorisé."""
    autorises = {Role.admin, *roles}

    def verifier(utilisateur: Utilisateur = Depends(get_current_user)) -> Utilisateur:
        if utilisateur.role not in autorises:
            noms = ", ".join(sorted(r.value for r in autorises))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action non autorisée pour le rôle « {utilisateur.role.value} ». Rôles autorisés : {noms}.",
            )
        return utilisateur

    return verifier


class Pagination:
    def __init__(
        self,
        limit: int = Query(LIMIT_DEFAUT, ge=1, le=LIMIT_MAX, description="Nombre d'éléments (max 100)"),
        offset: int = Query(0, ge=0, description="Nombre d'éléments à sauter"),
    ):
        self.limit = limit
        self.offset = offset
