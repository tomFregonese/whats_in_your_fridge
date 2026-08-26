"""Domain-level exceptions raised by services.

Controllers never catch these individually — `main.py` registers one
FastAPI exception handler per type, mapping each to the right HTTP status.
This keeps controllers thin: they call a service and return a Dto, nothing
else.
"""


class NotFoundError(Exception):
    """A requested resource does not exist."""


class AlreadyOnboardedError(Exception):
    """Onboarding was attempted after it had already completed."""


class NotOnboardedError(Exception):
    """A setting was requested before onboarding has completed."""
