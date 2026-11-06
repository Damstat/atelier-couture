"""Règles de gestion des commandes."""
from collections.abc import Iterable
from datetime import date, timedelta
from uuid import uuid4

from sqlalchemy import and_, not_, select
from sqlalchemy.orm import Session

from app.exceptions import Conflit, DonneesInvalides, Interdit, Introuvable
from app.models import Client, Commande, HistoriqueStatut, LigneCommande, Mesure, TypeVetement, Utilisateur
from app.models.enums import Role, StatutCommande
from app.schemas.commande import ChangementStatut, CommandeCreate, CommandeUpdate, LigneCreate
from app.services.pagination import paginer
from app.services.workflow import verifier_transition

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


def condition_en_retard(aujourd_hui: date | None = None):
    """RG11 en SQL : date prévue dépassée, ni livrée ni annulée."""
    aujourd_hui = aujourd_hui or date.today()
    return and_(
        Commande.date_livraison_prevue < aujourd_hui,
        Commande.statut.not_in(list(STATUTS_FINAUX)),
    )


def lister_commandes(
    db: Session, limit: int, offset: int, *,
    statut: StatutCommande | None = None, client_id: int | None = None,
    en_retard: bool | None = None, date_min: date | None = None,
    date_max: date | None = None, numero: str | None = None,
) -> tuple[list[Commande], int]:
    """Commandes filtrées, la plus récente d'abord. date_min et date_max portent sur la date de commande."""
    if date_min and date_max and date_min > date_max:
        raise DonneesInvalides("date_min ne peut pas être postérieure à date_max.")
    requete = select(Commande)
    if statut is not None:
        requete = requete.where(Commande.statut == statut)
    if client_id is not None:
        requete = requete.where(Commande.client_id == client_id)
    if en_retard is not None:
        cond = condition_en_retard()
        requete = requete.where(cond if en_retard else not_(cond))
    if date_min is not None:
        requete = requete.where(Commande.date_commande >= date_min)
    if date_max is not None:
        requete = requete.where(Commande.date_commande <= date_max)
    if numero:
        requete = requete.where(Commande.numero.ilike(f"%{numero.strip()}%"))
    requete = requete.order_by(Commande.date_commande.desc(), Commande.id.desc())
    return paginer(db, requete, limit, offset)


def obtenir_commande(db: Session, commande_id: int) -> Commande:
    commande = db.get(Commande, commande_id)
    if commande is None:
        raise Introuvable(f"Commande {commande_id} introuvable.")
    return commande


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


# ---------- Statuts ----------

def changer_statut(db: Session, commande_id: int, donnees: ChangementStatut, auteur: Utilisateur) -> Commande:
    commande = obtenir_commande(db, commande_id)
    demande = donnees.statut
    commentaire = (donnees.commentaire or "").strip() or None

    # RG14 : le tailleur ne peut pas annuler une commande
    if demande == StatutCommande.annulee and auteur.role == Role.tailleur:
        raise Interdit("Le tailleur ne peut pas annuler une commande : adressez-vous à l'accueil.")
    # Workflow et RG13 (409 avec les statuts possibles)
    verifier_transition(commande.statut, demande)
    # RG14 : annuler une commande qui a reçu un acompte exige un commentaire
    if demande == StatutCommande.annulee and commande.montant_paye > 0 and commentaire is None:
        raise DonneesInvalides(
            f"Cette commande a reçu {commande.montant_paye} FCFA : indiquez dans « commentaire » "
            "le sort de l'argent (remboursement, avoir...)."
        )
    enregistrer_statut(commande, demande, auteur, commentaire)  # RG15
    db.flush()
    return commande


def historique_commande(db: Session, commande_id: int) -> list[dict]:
    """RG15 : changements de statut dans l'ordre chronologique."""
    commande = obtenir_commande(db, commande_id)
    return [
        {
            "id": h.id,
            "ancien_statut": h.ancien_statut,
            "nouveau_statut": h.nouveau_statut,
            "commentaire": h.commentaire,
            "utilisateur_id": h.utilisateur_id,
            "utilisateur_nom": h.utilisateur.nom_complet if h.utilisateur else None,
            "date_changement": h.date_changement,
        }
        for h in commande.historique  # relation triée par id = ordre d'insertion
    ]


# ---------- Modification ----------

def verifier_modifiable(commande: Commande) -> None:
    """RG12 : une commande livrée ou annulée n'est plus modifiable."""
    if commande.statut in STATUTS_FINAUX:
        raise Conflit(
            f"La commande {commande.numero} est « {commande.statut.value} » : elle n'est plus modifiable."
        )


def modifier_commande(db: Session, commande_id: int, donnees: CommandeUpdate) -> Commande:
    commande = obtenir_commande(db, commande_id)
    verifier_modifiable(commande)
    champs = donnees.model_dump(exclude_unset=True)

    if "mesure_id" in champs:
        mesure = choisir_mesure(db, commande.client, champs["mesure_id"]) if champs["mesure_id"] else None
        commande.mesure_id = mesure.id if mesure else None
    if "date_livraison_prevue" in champs:
        verifier_date_prevue(champs["date_livraison_prevue"], commande.date_commande)
        commande.date_livraison_prevue = champs["date_livraison_prevue"]
    if "remise" in champs:
        commande.remise = champs["remise"]
        recalculer_montants(commande)  # RG7
    if "notes" in champs:
        commande.notes = champs["notes"]
    db.flush()
    return commande


# ---------- Lignes (RG10) ----------

def verifier_lignes_modifiables(commande: Commande) -> None:
    """RG10 : les lignes ne sont modifiables que tant que la commande est « en_attente »."""
    if commande.statut != StatutCommande.en_attente:
        raise Conflit(
            f"Les prestations de la commande {commande.numero} ne sont plus modifiables : "
            f"elle est « {commande.statut.value} » (modifiable seulement en « en_attente »)."
        )


def ajouter_ligne(db: Session, commande_id: int, donnees: LigneCreate) -> Commande:
    commande = obtenir_commande(db, commande_id)
    verifier_lignes_modifiables(commande)
    commande.lignes.append(construire_ligne(db, donnees))  # RG6
    recalculer_montants(commande)  # RG7
    db.flush()
    return commande


def retirer_ligne(db: Session, commande_id: int, ligne_id: int) -> Commande:
    commande = obtenir_commande(db, commande_id)
    ligne = next((l for l in commande.lignes if l.id == ligne_id), None)
    if ligne is None:
        raise Introuvable(f"Ligne {ligne_id} introuvable dans la commande {commande.numero}.")
    verifier_lignes_modifiables(commande)
    if len(commande.lignes) == 1:
        raise Conflit("Une commande garde toujours au moins une prestation : ajoutez-en une autre avant de retirer celle-ci.")
    commande.lignes.remove(ligne)
    recalculer_montants(commande)  # RG7
    db.flush()
    return commande
