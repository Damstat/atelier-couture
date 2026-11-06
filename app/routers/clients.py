from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import Pagination, get_current_user, require_roles
from app.models.enums import Genre
from app.schemas.client import ClientCreate, ClientRead, ClientUpdate
from app.schemas.common import Page
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


@router.get("", response_model=Page[ClientRead], summary="Liste paginée des clients (triés par nom, prénom)")
def lister(
    q: str | None = Query(None, description="Recherche dans nom, prénom et téléphone (2 caractères minimum)"),
    genre: Genre | None = None,
    pagination: Pagination = Depends(),
    db: Session = Depends(get_db),
):
    items, total = service.lister_clients(db, pagination.limit, pagination.offset, q, genre)
    return Page[ClientRead](items=items, total=total, limit=pagination.limit, offset=pagination.offset)


@router.get("/{client_id}", response_model=ClientRead, summary="Fiche d'un client")
def detail(client_id: int, db: Session = Depends(get_db)):
    return service.obtenir_client(db, client_id)


@router.patch("/{client_id}", response_model=ClientRead, summary="Modification partielle d'un client")
def modifier(client_id: int, donnees: ClientUpdate, db: Session = Depends(get_db)):
    client = service.modifier_client(db, client_id, donnees)
    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_roles())],
               summary="Supprimer un client et ses mesures (admin, RG4)")
def supprimer(client_id: int, db: Session = Depends(get_db)):
    service.supprimer_client(db, client_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
