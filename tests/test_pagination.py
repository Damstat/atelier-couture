from sqlalchemy import select

from app.models import TypeVetement
from app.schemas.common import Page
from app.services.pagination import paginer


def test_paginer_renvoie_la_tranche_et_le_total(db):
    for i in range(5):
        db.add(TypeVetement(nom=f"P{i}", prix_base=1000, delai_jours=1))
    db.commit()

    items, total = paginer(db, select(TypeVetement).order_by(TypeVetement.nom), limit=2, offset=3)
    assert total == 5
    assert [t.nom for t in items] == ["P3", "P4"]

    page = Page[str](items=[t.nom for t in items], total=total, limit=2, offset=3)
    assert page.model_dump() == {"items": ["P3", "P4"], "total": 5, "limit": 2, "offset": 3}
