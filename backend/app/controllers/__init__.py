"""Thin HTTP controllers (FastAPI ``APIRouter``\\ s).

Each controller maps ``dto_in.to_domain()`` / ``XxxDtoOut.from_domain()``
at the boundary and delegates everything else to ``services/``. No business
logic lives here.
"""
