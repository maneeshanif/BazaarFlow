"""Unified exception hierarchy for BazaarFlow.

Replaces:
  - backend/exceptions.py (shim)
  - backend/src/exceptions.py (Facebook-only)
"""

from __future__ import annotations


class BazaarFlowError(Exception):
    """Base exception for all application errors."""


# -- Facebook / Meta -----------------------------------------------------------

class FacebookAPIError(BazaarFlowError):
    """Raised when the Facebook Graph API returns an error.

    ``error_code`` / ``error_subcode`` carry Graph API codes (for example 190 = expired token, 100 = invalid
    parameter) so callers can decide what to retry or tolerate.
    """

    def __init__(self, message: str = "", error_code: int | None = None, error_subcode: int | None = None) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.error_subcode = error_subcode


class PostCreationError(FacebookAPIError):
    """Raised when a Facebook post cannot be created."""


class ImageUploadError(FacebookAPIError):
    """Raised when an image cannot be uploaded to Facebook."""


class InvalidCredentialsError(FacebookAPIError):
    """Raised when Facebook credentials are missing or rejected."""


class TokenRefreshError(FacebookAPIError):
    """Raised when an access token cannot be refreshed."""


# -- Database ------------------------------------------------------------------

class RecordNotFoundError(BazaarFlowError):
    """Raised when a requested DB record does not exist."""


class DuplicateRecordError(BazaarFlowError):
    """Raised when a unique constraint would be violated."""


# -- Vendor / Auth -------------------------------------------------------------

class VendorNotFoundError(RecordNotFoundError):
    """Raised when a vendor lookup fails."""


class UnauthorizedError(BazaarFlowError):
    """Raised when a request lacks valid credentials."""


# -- WhatsApp / Webhook -------------------------------------------------------

class WebhookVerificationError(BazaarFlowError):
    """Raised when a webhook signature check fails."""


# -- Agent ---------------------------------------------------------------------

class AgentError(BazaarFlowError):
    """Raised when an AI agent encounters an unrecoverable error."""
