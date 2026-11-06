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


@router.get("", response_model=list[UtilisateurRead], summary="Liste des comptes (triés par nom)")
def lister(db: Session = Depends(get_db)):
    return service.lister_utilisateurs(db)


@router.get("/{utilisateur_id}", response_model=UtilisateurRead, summary="Détail d'un compte")
def detail(utilisateur_id: int, db: Session = Depends(get_db)):
    return service.obtenir_utilisateur(db, utilisateur_id)
