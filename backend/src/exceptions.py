"""Re-export custom exceptions for convenient imports."""

from exceptions import (
    ConfigurationError,
    FacebookAPIError,
    FacebookManagerError,
    ImageUploadError,
    InvalidCredentialsError,
    PostCreationError,
    VideoUploadError,
)

__all__ = [
    "ConfigurationError",
    "FacebookAPIError",
    "FacebookManagerError",
    "ImageUploadError",
    "InvalidCredentialsError",
    "PostCreationError",
    "VideoUploadError",
]
