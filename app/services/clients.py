from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import Conflit
from app.models import Client
from app.schemas.client import ClientCreate


def _verifier_telephone_libre(db: Session, telephone: str, sauf_id: int | None = None) -> None:
    """RG1 : le téléphone (déjà normalisé) identifie un seul client."""
    requete = select(Client).where(Client.telephone == telephone)
    if sauf_id is not None:
        requete = requete.where(Client.id != sauf_id)
    existant = db.scalar(requete)
    if existant is not None:
        raise Conflit(
            f"Le numéro {telephone} est déjà utilisé par le client n°{existant.id} "
            f"({existant.prenom} {existant.nom})."
        )


def creer_client(db: Session, donnees: ClientCreate) -> Client:
    _verifier_telephone_libre(db, donnees.telephone)
    client = Client(**donnees.model_dump())
    db.add(client)
    db.flush()
    return client
