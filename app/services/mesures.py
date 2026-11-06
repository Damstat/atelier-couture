from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import Conflit, DonneesInvalides, Introuvable
from app.models import Commande, Mesure, Utilisateur
from app.models.mesure import CHAMPS_MESURES
from app.schemas.mesure import MESSAGE_AUCUNE_MESURE, MesureCreate, MesureUpdate
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


def _plus_recentes_d_abord(client_id: int):
    return (
        select(Mesure)
        .where(Mesure.client_id == client_id)
        .order_by(Mesure.date_prise.desc(), Mesure.id.desc())
    )


def historique_mesures(db: Session, client_id: int) -> list[Mesure]:
    """RG3 : toutes les prises sont conservées, la plus récente d'abord."""
    obtenir_client(db, client_id)
    return list(db.scalars(_plus_recentes_d_abord(client_id)))


def dernieres_mesures(db: Session, client_id: int) -> Mesure | None:
    """RG3 : la prise de date la plus récente (None si le client n'en a aucune)."""
    return db.scalar(_plus_recentes_d_abord(client_id).limit(1))


def obtenir_dernieres_mesures(db: Session, client_id: int) -> Mesure:
    client = obtenir_client(db, client_id)
    mesure = dernieres_mesures(db, client_id)
    if mesure is None:
        raise Introuvable(f"Le client {client.prenom} {client.nom} n'a encore aucune prise de mesures.")
    return mesure


def obtenir_mesure(db: Session, mesure_id: int) -> Mesure:
    mesure = db.get(Mesure, mesure_id)
    if mesure is None:
        raise Introuvable(f"Prise de mesures {mesure_id} introuvable.")
    return mesure


def modifier_mesure(db: Session, mesure_id: int, donnees: MesureUpdate) -> Mesure:
    """Corrige une erreur de saisie ; la prise doit garder au moins une mesure (RG2)."""
    mesure = obtenir_mesure(db, mesure_id)
    champs = donnees.model_dump(exclude_unset=True)
    for champ, valeur in champs.items():
        setattr(mesure, champ, valeur)
    if all(getattr(mesure, c) is None for c in CHAMPS_MESURES):
        raise DonneesInvalides(f"Correction refusée : {MESSAGE_AUCUNE_MESURE}.")
    db.flush()
    return mesure


def supprimer_mesure(db: Session, mesure_id: int) -> None:
    """RG4 : une prise utilisée par une commande ne peut pas être supprimée."""
    mesure = obtenir_mesure(db, mesure_id)
    numeros = list(db.scalars(select(Commande.numero).where(Commande.mesure_id == mesure.id)))
    if numeros:
        raise Conflit(
            f"Impossible de supprimer cette prise de mesures : elle est utilisée par "
            f"la/les commande(s) {', '.join(numeros)}."
        )
    db.delete(mesure)
    db.flush()
