"""
Configuration management for Facebook Manager Tool
Handles environment variables and credentials validation
"""

import os
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class FacebookConfig(BaseSettings):
    """
    Configuration settings for Facebook API integration.
    Automatically loads from environment variables.
    """
    
    facebook_page_id: str = Field(
        ...,
        description="Facebook Page ID",
        validation_alias="FACEBOOK_PAGE_ID"
    )
    
    facebook_access_token: str = Field(
        ...,
        description="Facebook Page Access Token",
        validation_alias="FACEBOOK_ACCESS_TOKEN"
    )
    
    facebook_api_version: str = Field(
        default="v24.0",
        description="Facebook Graph API version",
        validation_alias="FACEBOOK_API_VERSION"
    )
    
    facebook_api_base_url: str = Field(
        default="https://graph.facebook.com",
        description="Facebook Graph API base URL",
        validation_alias="FACEBOOK_API_BASE_URL"
    )
    
    request_timeout: int = Field(
        default=30,
        description="HTTP request timeout in seconds",
        validation_alias="REQUEST_TIMEOUT"
    )
    
    max_retries: int = Field(
        default=3,
        description="Maximum number of retry attempts for failed requests",
        validation_alias="MAX_RETRIES"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True
    )
    
    @field_validator("facebook_page_id")
    @classmethod
    def validate_page_id(cls, v: str) -> str:
        """Validate Facebook Page ID format"""
        clean_value = v.strip() if isinstance(v, str) else v
        if not clean_value:
            raise ValueError("Facebook Page ID cannot be empty")
        if not clean_value.isdigit():
            raise ValueError("Facebook Page ID must be numeric")
        return clean_value
    
    @field_validator("facebook_access_token")
    @classmethod
    def validate_access_token(cls, v: str) -> str:
        """Validate Facebook Access Token format"""
        if not v or not v.strip():
            raise ValueError("Facebook Access Token cannot be empty")
        if len(v.strip()) < 20:
            raise ValueError("Facebook Access Token appears to be invalid (too short)")
        return v.strip()
    
    @field_validator("facebook_api_version")
    @classmethod
    def validate_api_version(cls, v: str) -> str:
        """Validate API version format"""
        if not v.startswith("v"):
            raise ValueError("API version must start with 'v' (e.g., v18.0)")
        return v
    
    @property
    def graph_api_url(self) -> str:
        """Construct the full Graph API base URL"""
        return f"{self.facebook_api_base_url}/{self.facebook_api_version}"
    
    @property
    def page_endpoint(self) -> str:
        """Get the page endpoint URL"""
        return f"{self.graph_api_url}/{self.facebook_page_id}"


def load_config(env_file: Optional[str] = None, use_env_file: bool = True) -> FacebookConfig:
    """
    Load and validate Facebook configuration.
    
    Args:
        env_file: Optional path to .env file. If None, uses default .env
        
    Returns:
        Validated FacebookConfig instance
        
    Raises:
        ValidationError: If configuration is invalid
        FileNotFoundError: If specified env_file doesn't exist
    """
    if env_file and not os.path.exists(env_file):
        raise FileNotFoundError(f"Environment file not found: {env_file}")
    
    if env_file:
        return FacebookConfig(_env_file=env_file)
    
    if not use_env_file:
        return FacebookConfig(_env_file=None)
    
    return FacebookConfig()


# Singleton instance (optional, for convenience)
_config_instance: Optional[FacebookConfig] = None


def get_config(reload: bool = False) -> FacebookConfig:
    """
    Get the global configuration instance.
    
    Args:
        reload: If True, reload configuration from environment
        
    Returns:
        FacebookConfig instance
    """
    global _config_instance
    
    if _config_instance is None or reload:
        _config_instance = load_config()
    
    return _config_instance