from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


def paginer(db: Session, requete: Select, limit: int, offset: int) -> tuple[list[Any], int]:
    """Exécute la requête paginée et renvoie (éléments, total sans pagination)."""
    total = db.scalar(select(func.count()).select_from(requete.order_by(None).subquery()))
    items = list(db.scalars(requete.limit(limit).offset(offset)))
    return items, total or 0
