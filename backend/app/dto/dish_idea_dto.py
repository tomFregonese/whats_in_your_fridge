from __future__ import annotations

from pydantic import BaseModel

from app.domain.dish_idea import DishIdea


class DishIdeaDtoOut(BaseModel):
    """`index` is the idea's position in the proposed shortlist — the
    stable key the frontend selects by and `POST .../select` accepts,
    since ideas aren't persisted with their own id (see `DishIdea`'s
    docstring)."""

    index: int
    dish_name: str
    description: str

    @classmethod
    def from_domain(cls, index: int, idea: DishIdea) -> DishIdeaDtoOut:
        return cls(index=index, dish_name=idea.dish_name, description=idea.description)
