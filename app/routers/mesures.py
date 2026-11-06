from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models import Utilisateur
from app.models.enums import Role
from app.schemas.mesure import MesureCreate, MesureRead
from app.services import mesures as service

router = APIRouter(tags=["Mesures"], dependencies=[Depends(get_current_user)])
tailleur = require_roles(Role.tailleur)


@router.post("/clients/{client_id}/mesures", response_model=MesureRead,
             status_code=status.HTTP_201_CREATED, summary="Nouvelle prise de mesures (tailleur, RG2)")
def creer(client_id: int, donnees: MesureCreate, db: Session = Depends(get_db),
          auteur: Utilisateur = Depends(tailleur)):
    mesure = service.creer_mesure(db, client_id, donnees, auteur)
    db.commit()
    db.refresh(mesure)
    return mesure


@router.get("/clients/{client_id}/mesures", response_model=list[MesureRead],
            summary="Historique des mesures, la plus récente d'abord (RG3)")
def historique(client_id: int, db: Session = Depends(get_db)):
    return service.historique_mesures(db, client_id)


@router.get("/clients/{client_id}/mesures/derniere", response_model=MesureRead,
            summary="Dernières mesures du client ; 404 s'il n'en a aucune")
def derniere(client_id: int, db: Session = Depends(get_db)):
    return service.obtenir_dernieres_mesures(db, client_id)


@router.get("/mesures/{mesure_id}", response_model=MesureRead, summary="Une prise de mesures")
def detail(mesure_id: int, db: Session = Depends(get_db)):
    return service.obtenir_mesure(db, mesure_id)
