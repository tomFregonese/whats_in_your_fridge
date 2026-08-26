"""Repositories — the only layer that touches a DB session.

Each repository calls ``entity.to_domain()`` / ``XxxEntity.from_domain(bo)``
and returns/accepts BOs (``domain/``) only. It never reimplements mapping
logic itself and is never called from ``controllers/`` directly — only from
``services/``.
"""
