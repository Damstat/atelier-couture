from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.exceptions import Conflit, Introuvable
from app.models import TypeVetement
from app.schemas.catalogue import TypeVetementCreate


def _verifier_nom_libre(db: Session, nom: str, sauf_id: int | None = None) -> None:
    requete = select(TypeVetement.id).where(func.lower(TypeVetement.nom) == nom.lower())
    if sauf_id is not None:
        requete = requete.where(TypeVetement.id != sauf_id)
    if db.scalar(requete) is not None:
        raise Conflit(f"Une prestation nommée « {nom} » existe déjà dans le catalogue.")


def creer_prestation(db: Session, donnees: TypeVetementCreate) -> TypeVetement:
    _verifier_nom_libre(db, donnees.nom)
    prestation = TypeVetement(**donnees.model_dump(), actif=True)
    db.add(prestation)
    db.flush()
    return prestation


def lister_prestations(db: Session, actifs_seulement: bool = True) -> list[TypeVetement]:
    requete = select(TypeVetement).order_by(TypeVetement.nom)
    if actifs_seulement:
        requete = requete.where(TypeVetement.actif.is_(True))
    return list(db.scalars(requete))


def obtenir_prestation(db: Session, prestation_id: int) -> TypeVetement:
    prestation = db.get(TypeVetement, prestation_id)
    if prestation is None:
        raise Introuvable(f"Prestation {prestation_id} introuvable dans le catalogue.")
    return prestation
