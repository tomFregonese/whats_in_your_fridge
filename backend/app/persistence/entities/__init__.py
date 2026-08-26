"""Persistence entities (Entity).

SQLModel ``table=True`` classes — the ONLY place the ORM is used. Used
exclusively from ``persistence/repositories/``, never imported outside this
layer. Each ``XxxEntity`` carries ``to_domain()`` / ``from_domain()`` to
convert to/from its ``domain/`` BO counterpart.
"""
