from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models import Utilisateur
from app.models.enums import Role
from app.schemas.paiement import PaiementCreate, PaiementRead
from app.services import paiements as service

router = APIRouter(tags=["Paiements"], dependencies=[Depends(get_current_user)])
accueil = require_roles(Role.accueil)


@router.post("/commandes/{commande_id}/paiements", response_model=PaiementRead,
             status_code=status.HTTP_201_CREATED, summary="Encaisser un acompte ou le solde (accueil, RG16)")
def encaisser(commande_id: int, donnees: PaiementCreate, db: Session = Depends(get_db),
              auteur: Utilisateur = Depends(accueil)):
    paiement = service.encaisser(db, commande_id, donnees, auteur)
    db.commit()
    db.refresh(paiement)
    return paiement
