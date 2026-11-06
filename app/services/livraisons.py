"""Livraisons (RG18 à RG20)."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import Conflit, DonneesInvalides, Introuvable
from app.models import Commande, Livraison, Utilisateur
from app.models.enums import ModeLivraison, StatutCommande, StatutLivraison
from app.schemas.livraison import ConfirmationLivraison, LivraisonPlanification, LivraisonRead
from app.services.commandes import (
    enregistrer_statut, obtenir_commande, solde, verifier_date_prevue, verifier_modifiable,
)


def planifier(db: Session, commande_id: int, donnees: LivraisonPlanification) -> Livraison:
    commande = obtenir_commande(db, commande_id)
    verifier_modifiable(commande)  # 409 si livrée ou annulée

    adresse = (donnees.adresse or "").strip() or None
    # RG18 : une livraison à domicile exige une adresse
    if donnees.mode == ModeLivraison.domicile and adresse is None:
        raise DonneesInvalides("Une livraison à domicile exige une adresse.")
    verifier_date_prevue(donnees.date_prevue, commande.date_commande)

    # RG18 : replanifier modifie la livraison existante, sans en créer une seconde
    livraison = commande.livraison or Livraison(statut=StatutLivraison.planifiee)
    livraison.mode = donnees.mode
    livraison.date_prevue = donnees.date_prevue
    livraison.adresse = adresse
    livraison.livreur = donnees.livreur
    livraison.notes = donnees.notes
    commande.livraison = livraison

    # RG18 : planifier met à jour la date de livraison prévue de la commande
    commande.date_livraison_prevue = donnees.date_prevue
    db.flush()
    return livraison


def tournee(
    db: Session, statut: StatutLivraison | None = None,
    date_min: date | None = None, date_max: date | None = None,
) -> list[dict]:
    """Liste de tournée triée par date prévue, avec les infos utiles au livreur."""
    if date_min and date_max and date_min > date_max:
        raise DonneesInvalides("date_min ne peut pas être postérieure à date_max.")
    requete = select(Livraison)
    if statut is not None:
        requete = requete.where(Livraison.statut == statut)
    if date_min is not None:
        requete = requete.where(Livraison.date_prevue >= date_min)
    if date_max is not None:
        requete = requete.where(Livraison.date_prevue <= date_max)
    requete = requete.order_by(Livraison.date_prevue, Livraison.id)
    resultat = []
    for l in db.scalars(requete):
        c = l.commande
        resultat.append({
            **LivraisonRead.model_validate(l).model_dump(),
            "numero_commande": c.numero,
            "client_nom": f"{c.client.prenom} {c.client.nom}",
            "client_telephone": c.client.telephone,
            "solde_commande": solde(c),
        })
    return resultat


def obtenir_livraison(db: Session, commande_id: int) -> Livraison:
    commande = obtenir_commande(db, commande_id)
    if commande.livraison is None:
        raise Introuvable(f"Aucune livraison n'est planifiée pour la commande {commande.numero}.")
    return commande.livraison


def confirmer(db: Session, commande_id: int, donnees: ConfirmationLivraison, auteur: Utilisateur) -> Commande:
    """Remise du vêtement au client (RG19, RG20)."""
    commande = obtenir_commande(db, commande_id)

    # RG19 : la commande doit être « terminee »...
    if commande.statut != StatutCommande.terminee:
        raise Conflit(
            f"La commande {commande.numero} est « {commande.statut.value} » : "
            "seule une commande « terminee » peut être livrée."
        )
    date_effective = donnees.date_effective or date.today()
    if date_effective > date.today():
        raise DonneesInvalides("La date effective de livraison ne peut pas être dans le futur.")
    if date_effective < commande.date_commande:
        raise DonneesInvalides("La date effective de livraison ne peut pas précéder la date de commande.")

    # ... et soldée, sauf autorisation explicite (la dette reste alors visible)
    impaye = solde(commande)
    commentaire = None
    if impaye > 0:
        if not donnees.autoriser_solde_impaye:
            raise Conflit(
                f"Livraison refusée : il reste {impaye} FCFA à payer sur la commande {commande.numero}. "
                "Encaissez le solde ou envoyez autoriser_solde_impaye=true."
            )
        commentaire = f"Livrée avec un solde impayé de {impaye} FCFA (autorisé)."

    # RG20 : sans planification préalable, une livraison « retrait_atelier » est créée
    livraison = commande.livraison or Livraison(
        mode=ModeLivraison.retrait_atelier, date_prevue=commande.date_livraison_prevue,
    )
    livraison.statut = StatutLivraison.livree
    livraison.date_effective = date_effective
    commande.livraison = livraison
    commande.date_livraison_reelle = date_effective
    enregistrer_statut(commande, StatutCommande.livree, auteur, commentaire)  # RG15
    db.flush()
    return commande
