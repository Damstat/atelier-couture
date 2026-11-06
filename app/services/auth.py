from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.exceptions import NonAuthentifie
from app.models import Utilisateur
from app.security import hacher_mot_de_passe, verifier_mot_de_passe

# RG23 : même message que l'e-mail soit inconnu ou le mot de passe faux
MESSAGE_IDENTIFIANTS = "E-mail ou mot de passe incorrect."
MESSAGE_DESACTIVE = "Ce compte est désactivé. Contactez l'administrateur."

# Hash factice : la vérification prend le même temps même si l'e-mail est inconnu
_HASH_FACTICE = hacher_mot_de_passe("mot-de-passe-factice")


def authentifier(db: Session, email: str, mot_de_passe: str) -> Utilisateur:
    utilisateur = db.scalar(
        select(Utilisateur).where(func.lower(Utilisateur.email) == email.strip().lower())
    )
    if utilisateur is None:
        verifier_mot_de_passe(mot_de_passe, _HASH_FACTICE)
        raise NonAuthentifie(MESSAGE_IDENTIFIANTS)
    if not verifier_mot_de_passe(mot_de_passe, utilisateur.mot_de_passe_hash):
        raise NonAuthentifie(MESSAGE_IDENTIFIANTS)
    if not utilisateur.actif:
        raise NonAuthentifie(MESSAGE_DESACTIVE)
    return utilisateur
