import re

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.exceptions import Conflit, DonneesInvalides, Introuvable
from app.models import Client, Commande
from app.models.enums import Genre
from app.services.pagination import paginer
from app.schemas.client import ClientCreate, ClientUpdate


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


def obtenir_client(db: Session, client_id: int) -> Client:
    client = db.get(Client, client_id)
    if client is None:
        raise Introuvable(f"Client {client_id} introuvable.")
    return client


def modifier_client(db: Session, client_id: int, donnees: ClientUpdate) -> Client:
    client = obtenir_client(db, client_id)
    champs = donnees.model_dump(exclude_unset=True)
    if "telephone" in champs:
        # Garder son propre numéro n'est pas un doublon
        _verifier_telephone_libre(db, champs["telephone"], sauf_id=client.id)
    for champ, valeur in champs.items():
        setattr(client, champ, valeur)
    db.flush()
    return client


def supprimer_client(db: Session, client_id: int) -> None:
    """RG4 : refusé si le client a des commandes ; ses mesures sont supprimées avec lui."""
    client = obtenir_client(db, client_id)
    nb = db.scalar(select(func.count()).select_from(Commande).where(Commande.client_id == client.id))
    if nb:
        raise Conflit(
            f"Impossible de supprimer le client {client.prenom} {client.nom} : "
            f"il a {nb} commande(s) enregistrée(s)."
        )
    db.delete(client)
    db.flush()
