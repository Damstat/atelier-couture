from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.schemas.catalogue import TypeVetementCreate, TypeVetementRead
from app.services import catalogue as service

router = APIRouter(prefix="/catalogue", tags=["Catalogue"], dependencies=[Depends(get_current_user)])


@router.post("", response_model=TypeVetementRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_roles())], summary="Ajouter une prestation (admin)")
def creer(donnees: TypeVetementCreate, db: Session = Depends(get_db)):
    prestation = service.creer_prestation(db, donnees)
    db.commit()
    db.refresh(prestation)
    return prestation
