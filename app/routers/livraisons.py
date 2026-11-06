from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models import Utilisateur
from app.models.enums import Role
from app.schemas.commande import CommandeDetail
from app.schemas.livraison import ConfirmationLivraison, LivraisonPlanification, LivraisonRead
from app.services import livraisons as service
from app.services.commandes import vers_detail

router = APIRouter(tags=["Livraisons"], dependencies=[Depends(get_current_user)])
accueil = require_roles(Role.accueil)


@router.put("/commandes/{commande_id}/livraison", response_model=LivraisonRead,
            dependencies=[Depends(accueil)], summary="Planifier ou replanifier la livraison (accueil, RG18)")
def planifier(commande_id: int, donnees: LivraisonPlanification, db: Session = Depends(get_db)):
    livraison = service.planifier(db, commande_id, donnees)
    db.commit()
    db.refresh(livraison)
    return livraison


@router.get("/commandes/{commande_id}/livraison", response_model=LivraisonRead,
            summary="Livraison de la commande ; 404 si aucune n'est planifiée")
def detail(commande_id: int, db: Session = Depends(get_db)):
    return service.obtenir_livraison(db, commande_id)


@router.post("/commandes/{commande_id}/livraison/confirmer", response_model=CommandeDetail,
             summary="Confirmer la remise au client (accueil, RG19, RG20)")
def confirmer(commande_id: int, donnees: ConfirmationLivraison | None = None,
              db: Session = Depends(get_db), auteur: Utilisateur = Depends(accueil)):
    commande = service.confirmer(db, commande_id, donnees or ConfirmationLivraison(), auteur)
    db.commit()
    db.refresh(commande)
    return vers_detail(commande)
