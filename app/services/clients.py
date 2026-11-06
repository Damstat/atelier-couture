import re

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.exceptions import Conflit, DonneesInvalides
from app.models import Client
from app.models.enums import Genre
from app.services.pagination import paginer
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


def lister_clients(
    db: Session, limit: int, offset: int, q: str | None = None, genre: Genre | None = None
) -> tuple[list[Client], int]:
    """Clients triés par nom puis prénom ; q cherche dans nom, prénom et téléphone."""
    requete = select(Client)
    if q is not None:
        q = q.strip()
        if len(q) < 2:
            raise DonneesInvalides("La recherche « q » doit contenir au moins 2 caractères.")
        motif = f"%{q}%"
        conditions = [Client.nom.ilike(motif), Client.prenom.ilike(motif)]
        chiffres = re.sub(r"[\s.\-()]", "", q)  # « 77 123 » trouve « 771234567 »
        if chiffres:
            conditions.append(Client.telephone.like(f"%{chiffres}%"))
        requete = requete.where(or_(*conditions))
    if genre is not None:
        requete = requete.where(Client.genre == genre)
    requete = requete.order_by(Client.nom, Client.prenom, Client.id)
    return paginer(db, requete, limit, offset)
