"""
Unit tests for configuration management
"""

import os
import pytest
from pydantic import ValidationError

from src.config import FacebookConfig, load_config, get_config


class TestFacebookConfig:
    """Test cases for FacebookConfig"""
    
    def test_valid_config(self, monkeypatch):
        """Test creating a valid configuration"""
        monkeypatch.setenv("FACEBOOK_PAGE_ID", "123456789")
        monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "EAAtest123456789012345")
        
        config = FacebookConfig()
        
        assert config.facebook_page_id == "123456789"
        assert config.facebook_access_token == "EAAtest123456789012345"
        assert config.facebook_api_version == "v18.0"
        assert config.request_timeout == 30
        assert config.max_retries == 3
    
    def test_custom_api_version(self, monkeypatch):
        """Test setting custom API version"""
        monkeypatch.setenv("FACEBOOK_PAGE_ID", "123456789")
        monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "EAAtest123456789012345")
        monkeypatch.setenv("FACEBOOK_API_VERSION", "v19.0")
        
        config = FacebookConfig()
        
        assert config.facebook_api_version == "v19.0"
    
    def test_custom_timeout_and_retries(self, monkeypatch):
        """Test setting custom timeout and retries"""
        monkeypatch.setenv("FACEBOOK_PAGE_ID", "123456789")
        monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "EAAtest123456789012345")
        monkeypatch.setenv("REQUEST_TIMEOUT", "60")
        monkeypatch.setenv("MAX_RETRIES", "5")
        
        config = FacebookConfig()
        
        assert config.request_timeout == 60
        assert config.max_retries == 5
    
    def test_missing_page_id_raises_error(self, monkeypatch):
        """Test that missing page ID raises validation error"""
        monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "EAAtest123456789012345")
        monkeypatch.delenv("FACEBOOK_PAGE_ID", raising=False)
        
        with pytest.raises(ValidationError) as exc_info:
            FacebookConfig()
        
        assert "facebook_page_id" in str(exc_info.value).lower()
    
    def test_missing_access_token_raises_error(self, monkeypatch):
        """Test that missing access token raises validation error"""
        monkeypatch.setenv("FACEBOOK_PAGE_ID", "123456789")
        monkeypatch.delenv("FACEBOOK_ACCESS_TOKEN", raising=False)
        
        with pytest.raises(ValidationError) as exc_info:
            FacebookConfig()
        
        assert "facebook_access_token" in str(exc_info.value).lower()
    
    def test_invalid_page_id_format(self, monkeypatch):
        """Test that non-numeric page ID raises error"""
        monkeypatch.setenv("FACEBOOK_PAGE_ID", "not-a-number")
        monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "EAAtest123456789012345")
        
        with pytest.raises(ValidationError) as exc_info:
            FacebookConfig()
        
        assert "must be numeric" in str(exc_info.value)
    
    def test_empty_page_id_raises_error(self, monkeypatch):
        """Test that empty page ID raises error"""
        monkeypatch.setenv("FACEBOOK_PAGE_ID", "")
        monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "EAAtest123456789012345")
        
        with pytest.raises(ValidationError) as exc_info:
            FacebookConfig()
        
        assert "cannot be empty" in str(exc_info.value)
    
    def test_short_access_token_raises_error(self, monkeypatch):
        """Test that too short access token raises error"""
        monkeypatch.setenv("FACEBOOK_PAGE_ID", "123456789")
        monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "short")
        
        with pytest.raises(ValidationError) as exc_info:
            FacebookConfig()
        
        assert "too short" in str(exc_info.value)
    
    def test_invalid_api_version_format(self, monkeypatch):
        """Test that API version without 'v' prefix raises error"""
        monkeypatch.setenv("FACEBOOK_PAGE_ID", "123456789")
        monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "EAAtest123456789012345")
        monkeypatch.setenv("FACEBOOK_API_VERSION", "18.0")
        
        with pytest.raises(ValidationError) as exc_info:
            FacebookConfig()
        
        assert "must start with 'v'" in str(exc_info.value)
    
    def test_graph_api_url_property(self, monkeypatch):
        """Test the graph_api_url property"""
        monkeypatch.setenv("FACEBOOK_PAGE_ID", "123456789")
        monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "EAAtest123456789012345")
        
        config = FacebookConfig()
        
        assert config.graph_api_url == "https://graph.facebook.com/v18.0"
    
    def test_page_endpoint_property(self, monkeypatch):
        """Test the page_endpoint property"""
        monkeypatch.setenv("FACEBOOK_PAGE_ID", "123456789")
        monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "EAAtest123456789012345")
        
        config = FacebookConfig()
        
        assert config.page_endpoint == "https://graph.facebook.com/v18.0/123456789"
    
    def test_whitespace_in_credentials_is_stripped(self, monkeypatch):
        """Test that whitespace is stripped from credentials"""
        monkeypatch.setenv("FACEBOOK_PAGE_ID", "  123456789  ")
        monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "  EAAtest123456789012345  ")
        
        config = FacebookConfig()
        
        assert config.facebook_page_id == "123456789"
        assert config.facebook_access_token == "EAAtest123456789012345"


class TestLoadConfig:
    """Test cases for load_config function"""
    
    def test_load_config_success(self, monkeypatch):
        """Test successful config loading"""
        monkeypatch.setenv("FACEBOOK_PAGE_ID", "123456789")
        monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "EAAtest123456789012345")
        
        config = load_config()
        
        assert isinstance(config, FacebookConfig)
        assert config.facebook_page_id == "123456789"
    
    def test_load_config_with_nonexistent_file(self):
        """Test loading config with non-existent file raises error"""
        with pytest.raises(FileNotFoundError):
            load_config(env_file="/nonexistent/path/.env")


class TestGetConfig:
    """Test cases for get_config singleton function"""
    
    def test_get_config_returns_same_instance(self, monkeypatch):
        """Test that get_config returns the same instance"""
        monkeypatch.setenv("FACEBOOK_PAGE_ID", "123456789")
        monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "EAAtest123456789012345")
        
        # Clear any existing instance
        from src import config as config_module
        config_module._config_instance = None
        
        config1 = get_config()
        config2 = get_config()
        
        assert config1 is config2
    
    def test_get_config_reload(self, monkeypatch):
        """Test that reload flag creates new instance"""
        monkeypatch.setenv("FACEBOOK_PAGE_ID", "123456789")
        monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "EAAtest123456789012345")
        
        # Clear any existing instance
        from src import config as config_module
        config_module._config_instance = None
        
        config1 = get_config()
        
        # Change environment
        monkeypatch.setenv("FACEBOOK_PAGE_ID", "987654321")
        
        config2 = get_config(reload=True)
        
        assert config1 is not config2
        assert config2.facebook_page_id == "987654321"
