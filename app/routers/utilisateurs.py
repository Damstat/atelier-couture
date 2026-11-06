from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_roles
from app.schemas.utilisateur import UtilisateurCreate, UtilisateurRead
from app.services import utilisateurs as service

# Toutes les routes : administrateur uniquement
router = APIRouter(
    prefix="/utilisateurs", tags=["Utilisateurs"], dependencies=[Depends(require_roles())]
)


@router.post("", response_model=UtilisateurRead, status_code=status.HTTP_201_CREATED,
             summary="Créer un compte")
def creer(donnees: UtilisateurCreate, db: Session = Depends(get_db)):
    utilisateur = service.creer_utilisateur(db, donnees)
    db.commit()
    db.refresh(utilisateur)
    return utilisateur
