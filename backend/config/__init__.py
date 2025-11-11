"""Configuration exports for the Facebook integration."""

from .fb_config import FacebookConfig, get_config, load_config

__all__ = [
    "FacebookConfig",
    "get_config",
    "load_config",
]
