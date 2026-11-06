from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models import Utilisateur
from app.models.enums import Role
from app.schemas.mesure import MesureCreate, MesureRead, MesureUpdate
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


@router.patch("/mesures/{mesure_id}", response_model=MesureRead, dependencies=[Depends(tailleur)],
              summary="Corriger une prise de mesures (tailleur)")
def modifier(mesure_id: int, donnees: MesureUpdate, db: Session = Depends(get_db)):
    mesure = service.modifier_mesure(db, mesure_id, donnees)
    db.commit()
    db.refresh(mesure)
    return mesure


@router.delete("/mesures/{mesure_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(tailleur)], summary="Supprimer une prise de mesures (tailleur, RG4)")
def supprimer(mesure_id: int, db: Session = Depends(get_db)):
    service.supprimer_mesure(db, mesure_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
