"""Statistiques de l'administrateur (routes 39 à 43).

Définitions (section 6) :
- chiffre d'affaires : total des commandes non annulées, daté à la date de commande ;
- encaissé : total des paiements reçus, daté à la date de paiement ;
- reste à encaisser : somme des soldes des commandes non annulées.
"""
from collections import defaultdict
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.exceptions import DonneesInvalides
from app.models import Client, Commande, LigneCommande, Livraison, Paiement, TypeVetement
from app.models.enums import StatutCommande, StatutLivraison
from app.services.commandes import condition_en_retard
from app.services.pagination import paginer

NON_ANNULEE = Commande.statut != StatutCommande.annulee


def periode(date_debut: date | None, date_fin: date | None) -> tuple[date, date]:
    """Par défaut : du 1er du mois à aujourd'hui. 422 si date_debut > date_fin."""
    aujourd_hui = date.today()
    debut = date_debut or aujourd_hui.replace(day=1)
    fin = date_fin or aujourd_hui
    if debut > fin:
        raise DonneesInvalides(
            f"date_debut ({debut.isoformat()}) ne peut pas être postérieure à date_fin ({fin.isoformat()})."
        )
    return debut, fin


def _somme(db: Session, expression, *conditions) -> int:
    return int(db.scalar(select(func.coalesce(func.sum(expression), 0)).where(*conditions)) or 0)


def tableau_de_bord(db: Session) -> dict:
    aujourd_hui = date.today()
    debut_mois = aujourd_hui.replace(day=1)
    du_mois = (NON_ANNULEE, Commande.date_commande >= debut_mois, Commande.date_commande <= aujourd_hui)

    par_statut = {s.value: 0 for s in StatutCommande}  # tous les statuts, même à 0
    for statut, nb in db.execute(select(Commande.statut, func.count()).group_by(Commande.statut)):
        par_statut[statut.value] = nb

    return {
        "chiffre_affaires_mois": _somme(db, Commande.montant_total, *du_mois),
        "encaisse_mois": _somme(
            db, Paiement.montant, Paiement.date_paiement >= debut_mois, Paiement.date_paiement <= aujourd_hui
        ),
        "nb_commandes_mois": db.scalar(select(func.count()).select_from(Commande).where(*du_mois)),
        "reste_a_encaisser": _somme(db, Commande.montant_total - Commande.montant_paye, NON_ANNULEE),
        "commandes_par_statut": par_statut,
        "nb_commandes_en_retard": db.scalar(
            select(func.count()).select_from(Commande).where(condition_en_retard(aujourd_hui))
        ),
        "commandes_pretes_a_livrer": par_statut[StatutCommande.terminee.value],
        "livraisons_du_jour": db.scalar(
            select(func.count()).select_from(Livraison).where(
                Livraison.date_prevue == aujourd_hui, Livraison.statut == StatutLivraison.planifiee
            )
        ),
    }


def chiffre_affaires(db: Session, granularite: str, date_debut: date | None, date_fin: date | None) -> dict:
    """CA (date de commande) et encaissements (date de paiement) par jour ou par mois."""
    debut, fin = periode(date_debut, date_fin)
    cle = (lambda d: d.isoformat()) if granularite == "jour" else (lambda d: d.strftime("%Y-%m"))
    lignes: dict[str, dict] = defaultdict(lambda: {"chiffre_affaires": 0, "encaisse": 0})

    for d, total in db.execute(
        select(Commande.date_commande, Commande.montant_total)
        .where(NON_ANNULEE, Commande.date_commande >= debut, Commande.date_commande <= fin)
    ):
        lignes[cle(d)]["chiffre_affaires"] += total
    for d, montant in db.execute(
        select(Paiement.date_paiement, Paiement.montant)
        .where(Paiement.date_paiement >= debut, Paiement.date_paiement <= fin)
    ):
        lignes[cle(d)]["encaisse"] += montant

    periodes = [{"periode": p, **v} for p, v in sorted(lignes.items())]  # seulement les périodes actives
    return {
        "granularite": granularite,
        "date_debut": debut,
        "date_fin": fin,
        "periodes": periodes,
        "total_chiffre_affaires": sum(p["chiffre_affaires"] for p in periodes),
        "total_encaisse": sum(p["encaisse"] for p in periodes),
    }


def par_type_vetement(db: Session, date_debut: date | None, date_fin: date | None) -> list[dict]:
    """Quantité vendue et CA avant remise par prestation, du plus élevé au plus faible."""
    debut, fin = periode(date_debut, date_fin)
    ca = func.sum(LigneCommande.quantite * LigneCommande.prix_unitaire)
    requete = (
        select(TypeVetement.id, TypeVetement.nom, func.sum(LigneCommande.quantite), ca)
        .join(LigneCommande, LigneCommande.type_vetement_id == TypeVetement.id)
        .join(Commande, Commande.id == LigneCommande.commande_id)
        .where(NON_ANNULEE, Commande.date_commande >= debut, Commande.date_commande <= fin)
        .group_by(TypeVetement.id, TypeVetement.nom)
        .order_by(ca.desc(), TypeVetement.nom)
    )
    return [
        {"type_vetement_id": i, "nom": nom, "quantite_vendue": int(q), "chiffre_affaires": int(total)}
        for i, nom, q, total in db.execute(requete)
    ]


def top_clients(db: Session, date_debut: date | None, date_fin: date | None, limite: int) -> list[dict]:
    debut, fin = periode(date_debut, date_fin)
    ca = func.sum(Commande.montant_total)
    requete = (
        select(
            Client.id, Client.prenom, Client.nom, Client.telephone,
            func.count(Commande.id), ca, func.sum(Commande.montant_total - Commande.montant_paye),
        )
        .join(Commande, Commande.client_id == Client.id)
        .where(NON_ANNULEE, Commande.date_commande >= debut, Commande.date_commande <= fin)
        .group_by(Client.id, Client.prenom, Client.nom, Client.telephone)
        .order_by(ca.desc(), Client.nom, Client.prenom)
        .limit(limite)
    )
    return [
        {
            "client_id": i, "client_nom": f"{prenom} {nom}", "telephone": tel,
            "nb_commandes": nb, "chiffre_affaires": int(total), "solde_du": int(du),
        }
        for i, prenom, nom, tel, nb, total, du in db.execute(requete)
    ]


def impayes(db: Session, limit: int, offset: int) -> tuple[list[Commande], int]:
    """Commandes non annulées non soldées, les plus urgentes d'abord (date prévue la plus proche)."""
    requete = (
        select(Commande)
        .where(NON_ANNULEE, Commande.montant_total > Commande.montant_paye)
        .order_by(Commande.date_livraison_prevue, Commande.id)
    )
    return paginer(db, requete, limit, offset)
