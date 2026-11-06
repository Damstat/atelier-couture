from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models import Utilisateur
from app.models.enums import Role
from app.schemas.commande import CommandeCreate, CommandeDetail
from app.services import commandes as service

router = APIRouter(prefix="/commandes", tags=["Commandes"], dependencies=[Depends(get_current_user)])
accueil = require_roles(Role.accueil)


@router.post("", response_model=CommandeDetail, status_code=status.HTTP_201_CREATED,
             summary="Créer une commande (accueil) : numéro, montants et date prévue calculés")
def creer(donnees: CommandeCreate, db: Session = Depends(get_db), auteur: Utilisateur = Depends(accueil)):
    commande = service.creer_commande(db, donnees, auteur)
    db.commit()
    db.refresh(commande)
    return service.vers_detail(commande)
