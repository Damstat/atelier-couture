from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import Pagination, require_roles
from app.schemas.commande import CommandeResume
from app.schemas.common import Page
from app.schemas.statistiques import (
    ChiffreAffaires, Granularite, StatTypeVetement, TableauDeBord, TopClient,
)
from app.services import statistiques as service
from app.services.commandes import vers_resume

# Administrateur uniquement
router = APIRouter(prefix="/statistiques", tags=["Statistiques"], dependencies=[Depends(require_roles())])

DEBUT = Query(None, description="Par défaut : le 1er du mois courant")
FIN = Query(None, description="Par défaut : aujourd'hui")


@router.get("/tableau-de-bord", response_model=TableauDeBord, summary="Indicateurs du mois courant")
def tableau_de_bord(db: Session = Depends(get_db)):
    return service.tableau_de_bord(db)


@router.get("/chiffre-affaires", response_model=ChiffreAffaires,
            summary="Chiffre d'affaires et encaissements par jour ou par mois")
def chiffre_affaires(granularite: Granularite = "jour", date_debut: date | None = DEBUT,
                     date_fin: date | None = FIN, db: Session = Depends(get_db)):
    return service.chiffre_affaires(db, granularite, date_debut, date_fin)


@router.get("/types-vetement", response_model=list[StatTypeVetement],
            summary="Quantité vendue et chiffre d'affaires (avant remise) par prestation")
def types_vetement(date_debut: date | None = DEBUT, date_fin: date | None = FIN,
                   db: Session = Depends(get_db)):
    return service.par_type_vetement(db, date_debut, date_fin)


@router.get("/top-clients", response_model=list[TopClient], summary="Meilleurs clients de la période")
def top_clients(date_debut: date | None = DEBUT, date_fin: date | None = FIN,
                limite: int = Query(10, ge=1, le=100), db: Session = Depends(get_db)):
    return service.top_clients(db, date_debut, date_fin, limite)


@router.get("/impayes", response_model=Page[CommandeResume],
            summary="Commandes non soldées, les plus urgentes d'abord")
def impayes(pagination: Pagination = Depends(), db: Session = Depends(get_db)):
    items, total = service.impayes(db, pagination.limit, pagination.offset)
    return Page[CommandeResume](
        items=[vers_resume(c) for c in items], total=total,
        limit=pagination.limit, offset=pagination.offset,
    )
