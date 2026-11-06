from datetime import date

from sqlalchemy.orm import Session

from app.models import Mesure, Utilisateur
from app.schemas.mesure import MesureCreate
from app.services.clients import obtenir_client


def creer_mesure(db: Session, client_id: int, donnees: MesureCreate, auteur: Utilisateur) -> Mesure:
    """Nouvelle prise de mesures : date du jour par défaut, prise par le tailleur connecté."""
    obtenir_client(db, client_id)
    valeurs = donnees.model_dump(exclude={"date_prise"})
    mesure = Mesure(
        client_id=client_id,
        date_prise=donnees.date_prise or date.today(),
        prise_par_id=auteur.id,
        **valeurs,
    )
    db.add(mesure)
    db.flush()
    return mesure
