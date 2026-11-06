from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_roles
from app.schemas.statistiques import ChiffreAffaires, Granularite, TableauDeBord
from app.services import statistiques as service

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
