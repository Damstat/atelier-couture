from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_roles
from app.schemas.statistiques import TableauDeBord
from app.services import statistiques as service

# Administrateur uniquement
router = APIRouter(prefix="/statistiques", tags=["Statistiques"], dependencies=[Depends(require_roles())])


@router.get("/tableau-de-bord", response_model=TableauDeBord, summary="Indicateurs du mois courant")
def tableau_de_bord(db: Session = Depends(get_db)):
    return service.tableau_de_bord(db)
