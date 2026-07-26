"""Shared, provider-neutral bot error taxonomy."""

from __future__ import annotations


class BotCoreError(Exception):
    """Base class for expected shared-core failures."""


class ConfigurationError(BotCoreError):
    """Raised when named runtime configuration is missing or unsafe."""


class ContractValidationError(BotCoreError):
    """Raised when a JSON value does not satisfy a versioned contract."""


class AuthorizationError(BotCoreError):
    """Raised when a caller is not allowed to perform an operation."""


class ResourceNotFoundError(BotCoreError):
    """Raised when an allowlisted domain resource does not exist."""


class ConflictError(BotCoreError):
    """Raised when optimistic state no longer matches."""


class ProviderUnavailableError(BotCoreError):
    """Raised when an injected external provider is unavailable."""


class NotConfiguredError(BotCoreError):
    """Raised when a safe fixture stub has no production provider."""


class LifecycleError(BotCoreError):
    """Raised when startup or shutdown cannot complete safely."""


class RateLimitedError(BotCoreError):
    """Provider rate limit with a bounded retry hint."""

    def __init__(self, retry_after_seconds: float) -> None:
        if retry_after_seconds < 0:
            raise ValueError("retry_after_seconds must be non-negative")
        self.retry_after_seconds = retry_after_seconds
        super().__init__("Provider rate limited the operation; retry later.")
