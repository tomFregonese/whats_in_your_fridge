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


class PasswordAlreadySetError(Exception):
    """The app password was set up more than once."""


class InvalidPasswordError(Exception):
    """An unlock attempt used the wrong app password (or none was ever set)."""


class VaultLockedError(Exception):
    """Something needed the encryption key before the vault was unlocked."""


class TokenNotConfiguredError(Exception):
    """The OpenRouter token was read before it had ever been set."""


class CatalogUnavailableError(Exception):
    """OpenRouter's model catalog couldn't be fetched."""


class OpenRouterError(Exception):
    """Base class for `agent.client` failures — callers that don't need to
    distinguish the specific cause can catch just this."""


class OpenRouterAuthError(OpenRouterError):
    """OpenRouter rejected the configured API token."""


class OpenRouterRateLimitError(OpenRouterError):
    """OpenRouter's rate limit was hit."""


class OpenRouterTimeoutError(OpenRouterError):
    """OpenRouter did not respond within the configured timeout."""


class OpenRouterConnectionError(OpenRouterError):
    """OpenRouter could not be reached at all (network/DNS/TLS failure)."""


class OpenRouterEmptyResponseError(OpenRouterError):
    """OpenRouter responded successfully but with no usable content."""
