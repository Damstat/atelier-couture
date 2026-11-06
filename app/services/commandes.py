"""Règles de gestion des commandes."""
from collections.abc import Iterable
from datetime import date, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.exceptions import Conflit, DonneesInvalides, Introuvable
from app.models import Client, Commande, HistoriqueStatut, LigneCommande, Mesure, TypeVetement, Utilisateur
from app.models.enums import StatutCommande
from app.schemas.commande import CommandeCreate, LigneCreate

STATUTS_FINAUX = {StatutCommande.livree, StatutCommande.annulee}


# ---------- Calculs (RG7, RG8) ----------

def sous_total_lignes(lignes: Iterable) -> int:
    """Somme des (quantité × prix unitaire)."""
    return sum(l.quantite * l.prix_unitaire for l in lignes)


def calculer_total(sous_total: int, remise: int) -> int:
    """RG7 : total = somme des prestations - remise ; la remise ne peut pas dépasser la somme."""
    if remise > sous_total:
        raise DonneesInvalides(
            f"La remise ({remise} FCFA) ne peut pas dépasser la somme des prestations ({sous_total} FCFA)."
        )
    return sous_total - remise


def verifier_total_couvre_paye(total: int, montant_paye: int) -> None:
    """RG7 : un changement ne peut jamais ramener le total sous le montant déjà payé."""
    if total < montant_paye:
        raise Conflit(
            f"Modification refusée : le nouveau total ({total} FCFA) serait inférieur "
            f"au montant déjà payé ({montant_paye} FCFA)."
        )


def recalculer_montants(commande: Commande) -> None:
    """Recalcule montant_total à partir des lignes et de la remise (RG7)."""
    total = calculer_total(sous_total_lignes(commande.lignes), commande.remise)
    verifier_total_couvre_paye(total, commande.montant_paye)
    commande.montant_total = total


def date_prevue_par_defaut(date_commande: date, delais_jours: Iterable[int]) -> date:
    """RG8 : date de commande + le plus long délai des prestations commandées."""
    return date_commande + timedelta(days=max(delais_jours, default=0))


def verifier_date_prevue(date_prevue: date, date_commande: date) -> None:
    """RG8 : la date prévue ne peut pas précéder la date de commande."""
    if date_prevue < date_commande:
        raise DonneesInvalides(
            f"La date de livraison prévue ({date_prevue.isoformat()}) ne peut pas précéder "
            f"la date de commande ({date_commande.isoformat()})."
        )


# ---------- Lecture ----------

def solde(commande: Commande) -> int:
    """RG7 : solde = total - payé."""
    return commande.montant_total - commande.montant_paye


def est_en_retard(commande: Commande, aujourd_hui: date | None = None) -> bool:
    """RG11 : date prévue dépassée et commande ni livrée ni annulée."""
    aujourd_hui = aujourd_hui or date.today()
    return commande.statut not in STATUTS_FINAUX and commande.date_livraison_prevue < aujourd_hui


def nom_client(commande: Commande) -> str:
    return f"{commande.client.prenom} {commande.client.nom}"


def vers_resume(commande: Commande) -> dict:
    """Données d'une commande en liste (avec client_nom, solde, en_retard)."""
    return {
        "id": commande.id,
        "numero": commande.numero,
        "client_id": commande.client_id,
        "client_nom": nom_client(commande),
        "statut": commande.statut,
        "date_commande": commande.date_commande,
        "date_livraison_prevue": commande.date_livraison_prevue,
        "date_livraison_reelle": commande.date_livraison_reelle,
        "remise": commande.remise,
        "montant_total": commande.montant_total,
        "montant_paye": commande.montant_paye,
        "solde": solde(commande),
        "en_retard": est_en_retard(commande),
    }


def vers_detail(commande: Commande) -> dict:
    """Détail complet : lignes (nom de la prestation, sous-total), paiements, livraison."""
    return {
        **vers_resume(commande),
        "mesure_id": commande.mesure_id,
        "notes": commande.notes,
        "cree_par_id": commande.cree_par_id,
        "lignes": [
            {
                "id": l.id,
                "type_vetement_id": l.type_vetement_id,
                "type_vetement_nom": l.type_vetement.nom,
                "description": l.description,
                "quantite": l.quantite,
                "prix_unitaire": l.prix_unitaire,
                "sous_total": l.quantite * l.prix_unitaire,
            }
            for l in commande.lignes
        ],
        "paiements": list(commande.paiements),
        "livraison": commande.livraison,
    }


# ---------- Création ----------

def numero_commande(annee: int, identifiant: int) -> str:
    """RG5 : CMD-AAAA-NNNNN, par exemple CMD-2026-00017."""
    return f"CMD-{annee}-{identifiant:05d}"


def enregistrer_statut(
    commande: Commande, nouveau: StatutCommande, auteur: Utilisateur,
    commentaire: str | None = None, initial: bool = False,
) -> None:
    """RG15 : chaque changement est inscrit dans l'historique (ancien statut vide à la création)."""
    ancien = None if initial else commande.statut
    commande.statut = nouveau
    commande.historique.append(HistoriqueStatut(
        ancien_statut=ancien, nouveau_statut=nouveau,
        commentaire=commentaire, utilisateur_id=auteur.id,
    ))


def construire_ligne(db: Session, donnees: LigneCreate) -> LigneCommande:
    """RG6 : prix du catalogue par défaut ; une prestation inactive ne peut plus être commandée."""
    prestation = db.get(TypeVetement, donnees.type_vetement_id)
    if prestation is None:
        raise Introuvable(f"Prestation {donnees.type_vetement_id} introuvable dans le catalogue.")
    if not prestation.actif:
        raise DonneesInvalides(
            f"La prestation « {prestation.nom} » a été retirée du catalogue et ne peut plus être commandée."
        )
    return LigneCommande(
        type_vetement=prestation,
        quantite=donnees.quantite,
        prix_unitaire=donnees.prix_unitaire if donnees.prix_unitaire is not None else prestation.prix_base,
        description=donnees.description,
    )


def choisir_mesure(db: Session, client: Client, mesure_id: int | None) -> Mesure | None:
    """RG9 : les mesures doivent appartenir au client ; sans précision, ses dernières mesures."""
    if mesure_id is None:
        from app.services.mesures import dernieres_mesures  # import local : évite un import circulaire

        return dernieres_mesures(db, client.id)
    mesure = db.get(Mesure, mesure_id)
    if mesure is None:
        raise Introuvable(f"Prise de mesures {mesure_id} introuvable.")
    if mesure.client_id != client.id:
        raise DonneesInvalides(
            f"La prise de mesures {mesure_id} n'appartient pas au client {client.prenom} {client.nom}."
        )
    return mesure


def creer_commande(db: Session, donnees: CommandeCreate, auteur: Utilisateur) -> Commande:
    client = db.get(Client, donnees.client_id)
    if client is None:
        raise Introuvable(f"Client {donnees.client_id} introuvable.")
    mesure = choisir_mesure(db, client, donnees.mesure_id)
    lignes = [construire_ligne(db, l) for l in donnees.lignes]

    aujourd_hui = date.today()
    date_prevue = donnees.date_livraison_prevue or date_prevue_par_defaut(
        aujourd_hui, [l.type_vetement.delai_jours for l in lignes]
    )
    verifier_date_prevue(date_prevue, aujourd_hui)

    commande = Commande(
        numero=f"TMP-{uuid4().hex[:20]}",  # remplacé dès que l'identifiant est connu
        client=client,
        mesure_id=mesure.id if mesure else None,
        date_commande=aujourd_hui,
        date_livraison_prevue=date_prevue,
        remise=donnees.remise,
        montant_paye=0,
        notes=donnees.notes,
        cree_par_id=auteur.id,
        lignes=lignes,
    )
    recalculer_montants(commande)
    enregistrer_statut(commande, StatutCommande.en_attente, auteur, initial=True)
    db.add(commande)
    db.flush()
    commande.numero = numero_commande(aujourd_hui.year, commande.id)
    db.flush()
    return commande
