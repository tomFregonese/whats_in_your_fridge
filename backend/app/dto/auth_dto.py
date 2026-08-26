from __future__ import annotations

from pydantic import BaseModel, Field

# Narrow action Dtos, no `to_domain()`/`from_domain()` — there's no BO on
# the other side of these (see `app.security`'s docstring for why).


class SetupPasswordDtoIn(BaseModel):
    password: str = Field(min_length=8)


class UnlockDtoIn(BaseModel):
    password: str = Field(min_length=1)


class AuthStatusDtoOut(BaseModel):
    password_set: bool
    unlocked: bool
