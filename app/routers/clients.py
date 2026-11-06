from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.client import ClientCreate, ClientRead
from app.services import clients as service

# Tout utilisateur connecté (sauf indication contraire sur la route)
router = APIRouter(prefix="/clients", tags=["Clients"], dependencies=[Depends(get_current_user)])


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED,
             summary="Créer un client (RG1 : téléphone unique et normalisé)")
def creer(donnees: ClientCreate, db: Session = Depends(get_db)):
    client = service.creer_client(db, donnees)
    db.commit()
    db.refresh(client)
    return client
