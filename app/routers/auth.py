from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.auth import Jeton
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
