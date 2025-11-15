"""Custom exceptions shared across the Facebook tooling."""


class FacebookManagerError(Exception):
    """Base exception for Facebook Manager errors."""


class FacebookAPIError(FacebookManagerError):
    """Exception raised when Facebook API returns an error."""

    def __init__(self, message: str, error_code: int = 0):
        self.message = message
        self.error_code = error_code
        super().__init__(f"Facebook API Error [{error_code}]: {message}")


class InvalidCredentialsError(FacebookAPIError):
    """Exception raised when Facebook credentials are invalid."""

    def __init__(self, message: str = "Invalid Facebook credentials"):
        super().__init__(message, error_code=190)


class PostCreationError(FacebookManagerError):
    """Exception raised when post creation fails."""


class ImageUploadError(FacebookManagerError):
    """Exception raised when image upload fails."""


class VideoUploadError(FacebookManagerError):
    """Exception raised when video upload fails."""


class ConfigurationError(FacebookManagerError):
    """Exception raised when configuration is invalid."""


__all__ = [
    "FacebookManagerError",
    "FacebookAPIError",
    "InvalidCredentialsError",
    "PostCreationError",
    "ImageUploadError",
    "VideoUploadError",
    "ConfigurationError",
]
