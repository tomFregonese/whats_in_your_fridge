"""API contract layer (Dto).

Pure Pydantic ``BaseModel`` classes exposed by the ``controllers/`` layer —
one ``XxxDtoIn`` per request payload, one ``XxxDtoOut`` per response. Never
import SQLModel or anything from ``persistence/`` here.

Each Dto carries its own mapping to/from the domain layer: ``XxxDtoIn`` gets
a ``to_domain()`` method, ``XxxDtoOut`` gets a ``from_domain()`` classmethod.
There is no separate "mapper" module — the conversion is part of the Dto's
own declaration.
"""
