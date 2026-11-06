from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Utilisateur
from app.schemas.auth import Jeton
from app.schemas.utilisateur import UtilisateurRead
from app.security import creer_jeton
from app.services import auth as service

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/login", response_model=Jeton, summary="Connexion (username = e-mail)")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    utilisateur = service.authentifier(db, form.username, form.password)
    return Jeton(
        access_token=creer_jeton(utilisateur.id),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UtilisateurRead, summary="Profil de l'utilisateur connecté")
def me(utilisateur: Utilisateur = Depends(get_current_user)):
    return utilisateur
