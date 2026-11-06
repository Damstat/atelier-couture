from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.exceptions import Conflit, Introuvable
from app.models import Utilisateur
from app.models.enums import Role
from app.schemas.utilisateur import UtilisateurCreate, UtilisateurUpdate
from app.security import hacher_mot_de_passe


def email_existe(db: Session, email: str) -> bool:
    return db.scalar(
        select(Utilisateur.id).where(func.lower(Utilisateur.email) == email.lower())
    ) is not None


def creer_utilisateur(db: Session, donnees: UtilisateurCreate) -> Utilisateur:
    email = donnees.email.strip().lower()
    if email_existe(db, email):
        raise Conflit(f"Un compte existe déjà avec l'e-mail {email}.")
    utilisateur = Utilisateur(
        email=email,
        nom_complet=donnees.nom_complet,
        mot_de_passe_hash=hacher_mot_de_passe(donnees.mot_de_passe),
        role=donnees.role,
        actif=True,
    )
    db.add(utilisateur)
    db.flush()
    return utilisateur


def lister_utilisateurs(db: Session) -> list[Utilisateur]:
    return list(db.scalars(select(Utilisateur).order_by(Utilisateur.nom_complet, Utilisateur.id)))


def obtenir_utilisateur(db: Session, utilisateur_id: int) -> Utilisateur:
    utilisateur = db.get(Utilisateur, utilisateur_id)
    if utilisateur is None:
        raise Introuvable(f"Utilisateur {utilisateur_id} introuvable.")
    return utilisateur


def modifier_utilisateur(
    db: Session, utilisateur_id: int, donnees: UtilisateurUpdate, auteur: Utilisateur
) -> Utilisateur:
    utilisateur = obtenir_utilisateur(db, utilisateur_id)
    champs = donnees.model_dump(exclude_unset=True)

    # RG24 : un administrateur ne peut ni se désactiver ni retirer son propre rôle admin
    if utilisateur.id == auteur.id:
        if champs.get("actif") is False:
            raise Conflit("Vous ne pouvez pas désactiver votre propre compte.")
        if "role" in champs and champs["role"] != Role.admin:
            raise Conflit("Vous ne pouvez pas retirer votre propre rôle d'administrateur.")

    if "mot_de_passe" in champs:
        utilisateur.mot_de_passe_hash = hacher_mot_de_passe(champs.pop("mot_de_passe"))
    for champ, valeur in champs.items():
        setattr(utilisateur, champ, valeur)
    db.flush()
    return utilisateur
