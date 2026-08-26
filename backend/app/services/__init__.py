"""Business logic layer.

Services manipulate BOs (``domain/``) only — never an Entity or a Dto.
They orchestrate ``persistence/repositories/`` and ``agent/``, and stay
testable without FastAPI or a database.
"""
