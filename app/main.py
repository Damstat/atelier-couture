from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import installer_gestionnaires
from app.routers import (
    auth, catalogue, clients, commandes, livraisons, mesures, paiements, statistiques, utilisateurs,
)

API_PREFIX = "/api/v1"

app = FastAPI(title="Atelier de couture", version="1.0.0")
installer_gestionnaires(app)

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(utilisateurs.router, prefix=API_PREFIX)
app.include_router(clients.router, prefix=API_PREFIX)
app.include_router(catalogue.router, prefix=API_PREFIX)
app.include_router(mesures.router, prefix=API_PREFIX)
app.include_router(commandes.router, prefix=API_PREFIX)
app.include_router(paiements.router, prefix=API_PREFIX)
app.include_router(livraisons.router, prefix=API_PREFIX)
app.include_router(statistiques.router, prefix=API_PREFIX)


@app.get("/health", tags=["Santé"], summary="État de l'API et de la base de données")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La base de données ne répond pas.",
        )
    return {"status": "ok"}
