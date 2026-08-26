from __future__ import annotations

from pydantic import BaseModel

from app.agent.catalog import FreeModel


class FreeModelDtoOut(BaseModel):
    id: str
    name: str
    context_length: int | None
    description: str | None

    @classmethod
    def from_domain(cls, model: FreeModel) -> FreeModelDtoOut:
        return cls(
            id=model.id,
            name=model.name,
            context_length=model.context_length,
            description=model.description,
        )


class ModelStatusDtoOut(BaseModel):
    model_id: str | None
    available: bool
