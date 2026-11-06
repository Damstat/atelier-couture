from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.enums import Role
from app.schemas.livraison import LivraisonPlanification, LivraisonRead
from app.services import livraisons as service

router = APIRouter(tags=["Livraisons"], dependencies=[Depends(get_current_user)])
accueil = require_roles(Role.accueil)


@router.put("/commandes/{commande_id}/livraison", response_model=LivraisonRead,
            dependencies=[Depends(accueil)], summary="Planifier ou replanifier la livraison (accueil, RG18)")
def planifier(commande_id: int, donnees: LivraisonPlanification, db: Session = Depends(get_db)):
    livraison = service.planifier(db, commande_id, donnees)
    db.commit()
    db.refresh(livraison)
    return livraison
