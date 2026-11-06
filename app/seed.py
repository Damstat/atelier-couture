"""Initialisation de la base : premier administrateur et catalogue de départ (annexe B).

Usage : python -m app.seed
Le script peut être relancé sans risque : il ne crée que ce qui manque.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import TypeVetement, Utilisateur
from app.models.enums import Role
from app.schemas.utilisateur import MDP_MIN
from app.security import hacher_mot_de_passe

# Annexe B : (nom, description, prix de base en FCFA, délai en jours)
CATALOGUE_DEPART = [
    ("Boubou", "Boubou homme en bazin ou brodé", 35000, 10),
    ("Costume 2 pièces", "Veste et pantalon", 85000, 14),
    ("Robe", "Robe sur mesure", 30000, 7),
    ("Ensemble wax", "Tenue deux pièces en wax", 25000, 7),
    ("Chemise", "Chemise sur mesure", 15000, 5),
    ("Pantalon", "Pantalon sur mesure", 12000, 4),
    ("Retouche", "Ourlet, rétrécissement, remplacement de fermeture", 3000, 2),
]


def creer_admin(db: Session, email: str, mot_de_passe: str, nom: str) -> str:
    """Crée le premier administrateur s'il n'existe pas. Renvoie un message de compte rendu."""
    email = (email or "").strip().lower()
    if not email or not mot_de_passe:
        return "Administrateur non créé : ADMIN_EMAIL et ADMIN_PASSWORD doivent être définis dans .env."
    if len(mot_de_passe) < MDP_MIN:
        raise ValueError(f"ADMIN_PASSWORD doit contenir au moins {MDP_MIN} caractères.")
    if db.scalar(select(Utilisateur).where(func.lower(Utilisateur.email) == email)):
        return f"Administrateur {email} : déjà présent."
    db.add(Utilisateur(
        email=email, nom_complet=nom or "Administrateur",
        mot_de_passe_hash=hacher_mot_de_passe(mot_de_passe), role=Role.admin, actif=True,
    ))
    return f"Administrateur {email} : créé."


def creer_catalogue(db: Session) -> str:
    """Ajoute les prestations de l'annexe B qui manquent (comparaison sur le nom)."""
    existants = {n.lower() for n in db.scalars(select(TypeVetement.nom))}
    ajouts = [
        TypeVetement(nom=nom, description=desc, prix_base=prix, delai_jours=delai, actif=True)
        for nom, desc, prix, delai in CATALOGUE_DEPART
        if nom.lower() not in existants
    ]
    db.add_all(ajouts)
    return f"Catalogue : {len(ajouts)} prestation(s) ajoutée(s), {len(CATALOGUE_DEPART) - len(ajouts)} déjà présente(s)."


def initialiser(db: Session, email: str, mot_de_passe: str, nom: str) -> list[str]:
    messages = [creer_admin(db, email, mot_de_passe, nom), creer_catalogue(db)]
    db.commit()
    return messages


def main() -> None:
    from app.config import settings
    from app.database import SessionLocal

    with SessionLocal() as db:
        for message in initialiser(db, settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD, settings.ADMIN_NOM):
            print(message)


if __name__ == "__main__":
    main()
