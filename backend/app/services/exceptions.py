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


class OpenRouterRequestError(OpenRouterError):
    """OpenRouter rejected the request itself (4xx/5xx) for a reason not
    covered by the more specific `OpenRouterError` subclasses above — e.g.
    a model that doesn't actually support the input it was sent (see
    `agent/dictation.py`'s audio calls), a malformed request, or an
    upstream 5xx. Carries whatever detail OpenRouter's response body gave,
    so it's diagnosable rather than an opaque failure."""


class AgentResponseInvalidError(Exception):
    """The model failed to produce a valid tool call after all retries."""


class ModelNotConfiguredError(Exception):
    """A suggestion was requested before an OpenRouter model was chosen."""


class ModelUnavailableError(Exception):
    """The configured OpenRouter model is no longer in the live `:free` catalog."""


class SttUnavailableError(Exception):
    """The local `stt` (speech-to-text) service couldn't be reached."""


class NlpUnavailableError(Exception):
    """The local `nlp` (dictation-structuring) service couldn't be reached."""
