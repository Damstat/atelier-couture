from fastapi import APIRouter, Depends, Response, status
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


@router.get("/commandes/{commande_id}/paiements", response_model=list[PaiementRead],
            summary="Paiements de la commande, dans l'ordre de saisie")
def lister(commande_id: int, db: Session = Depends(get_db)):
    return service.paiements_commande(db, commande_id)


@router.delete("/paiements/{paiement_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_roles())],
               summary="Annuler un paiement saisi par erreur (admin) ; recalcule le solde (RG17)")
def annuler(paiement_id: int, db: Session = Depends(get_db)):
    service.annuler_paiement(db, paiement_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
