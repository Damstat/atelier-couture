from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")

LIMIT_DEFAUT = 20
LIMIT_MAX = 100


class Page(BaseModel, Generic[T]):
    """Liste paginée : {"items": [...], "total": n, "limit": n, "offset": n}."""

    items: list[T]
    total: int
    limit: int
    offset: int
