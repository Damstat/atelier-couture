from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import Pagination, get_current_user, require_roles
from app.models import Utilisateur
from app.models.enums import Role, StatutCommande
from app.schemas.commande import (
    ChangementStatut, CommandeCreate, CommandeDetail, CommandeResume, CommandeUpdate, HistoriqueRead,
)
from app.schemas.common import Page
from app.services import commandes as service

router = APIRouter(prefix="/commandes", tags=["Commandes"], dependencies=[Depends(get_current_user)])
accueil = require_roles(Role.accueil)


@router.post("", response_model=CommandeDetail, status_code=status.HTTP_201_CREATED,
             summary="Créer une commande (accueil) : numéro, montants et date prévue calculés")
def creer(donnees: CommandeCreate, db: Session = Depends(get_db), auteur: Utilisateur = Depends(accueil)):
    commande = service.creer_commande(db, donnees, auteur)
    db.commit()
    db.refresh(commande)
    return service.vers_detail(commande)


@router.get("", response_model=Page[CommandeResume], summary="Liste paginée, la plus récente d'abord")
def lister(
    statut: StatutCommande | None = None,
    client_id: int | None = None,
    en_retard: bool | None = Query(None, description="Date prévue dépassée, ni livrée ni annulée (RG11)"),
    date_min: date | None = Query(None, description="Date de commande minimale"),
    date_max: date | None = Query(None, description="Date de commande maximale"),
    numero: str | None = Query(None, description="Tout ou partie du numéro"),
    pagination: Pagination = Depends(),
    db: Session = Depends(get_db),
):
    items, total = service.lister_commandes(
        db, pagination.limit, pagination.offset, statut=statut, client_id=client_id,
        en_retard=en_retard, date_min=date_min, date_max=date_max, numero=numero,
    )
    return Page[CommandeResume](
        items=[service.vers_resume(c) for c in items], total=total,
        limit=pagination.limit, offset=pagination.offset,
    )


@router.get("/{commande_id}", response_model=CommandeDetail,
            summary="Détail : lignes, paiements, livraison, solde, retard")
def detail(commande_id: int, db: Session = Depends(get_db)):
    return service.vers_detail(service.obtenir_commande(db, commande_id))


@router.post("/{commande_id}/statut", response_model=CommandeDetail,
             summary="Changer le statut selon le workflow (RG13, RG14)")
def changer_statut(commande_id: int, donnees: ChangementStatut, db: Session = Depends(get_db),
                   auteur: Utilisateur = Depends(get_current_user)):
    commande = service.changer_statut(db, commande_id, donnees, auteur)
    db.commit()
    db.refresh(commande)
    return service.vers_detail(commande)


@router.get("/{commande_id}/historique", response_model=list[HistoriqueRead],
            summary="Changements de statut, dans l'ordre chronologique (RG15)")
def historique(commande_id: int, db: Session = Depends(get_db)):
    return service.historique_commande(db, commande_id)


@router.patch("/{commande_id}", response_model=CommandeDetail, dependencies=[Depends(accueil)],
              summary="Modifier mesure, date prévue, remise, notes (accueil) ; montants recalculés")
def modifier(commande_id: int, donnees: CommandeUpdate, db: Session = Depends(get_db)):
    commande = service.modifier_commande(db, commande_id, donnees)
    db.commit()
    db.refresh(commande)
    return service.vers_detail(commande)
