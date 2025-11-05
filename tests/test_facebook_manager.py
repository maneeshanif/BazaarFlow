"""
Integration tests for Facebook Manager
Tests actual posting functionality with mocked HTTP requests
"""

import pytest
from unittest.mock import Mock, patch, mock_open, MagicMock
from pathlib import Path

from src.facebook_manager import FacebookManager
from src.config import FacebookConfig
from src.models import TextPostRequest, ImagePostRequest, FacebookPostResponse
from src.exceptions import (
    FacebookAPIError,
    InvalidCredentialsError,
    PostCreationError,
    ImageUploadError
)


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing"""
    return FacebookConfig(
        facebook_page_id="123456789",
        facebook_access_token="EAAtest123456789012345",
        facebook_api_version="v18.0",
        request_timeout=30,
        max_retries=3
    )


@pytest.fixture
def facebook_manager(mock_config):
    """Create a FacebookManager instance with mock config"""
    return FacebookManager(config=mock_config)


class TestFacebookManagerInit:
    """Test FacebookManager initialization"""
    
    def test_init_with_config(self, mock_config):
        """Test initialization with provided config"""
        manager = FacebookManager(config=mock_config)
        assert manager.config == mock_config
        assert manager.session is not None
    
    def test_init_without_config(self, monkeypatch):
        """Test initialization without config (loads from environment)"""
        monkeypatch.setenv("FACEBOOK_PAGE_ID", "123456789")
        monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "EAAtest123456789012345")
        
        manager = FacebookManager()
        assert manager.config is not None
        assert manager.config.facebook_page_id == "123456789"
    
    def test_context_manager(self, mock_config):
        """Test using FacebookManager as context manager"""
        with FacebookManager(config=mock_config) as manager:
            assert manager.session is not None
        
        # Session should be closed after context exit
        # Note: Can't easily test this without inspecting internal state


class TestCreateTextPost:
    """Test text post creation"""
    
    @patch('src.facebook_manager.requests.Session.request')
    def test_create_text_post_success(self, mock_request, facebook_manager):
        """Test successful text post creation"""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            'id': '123456789_987654321'
        }
        mock_request.return_value = mock_response
        
        post_request = TextPostRequest(message="Hello, Facebook!")
        response = facebook_manager.create_text_post(post_request)
        
        assert isinstance(response, FacebookPostResponse)
        assert response.post_id == '123456789_987654321'
        assert response.success is True
        
        # Verify the API was called correctly
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[1]['method'] == 'POST'
        assert '123456789/feed' in call_args[1]['url']
        assert call_args[1]['data']['message'] == "Hello, Facebook!"
    
    @patch('src.facebook_manager.requests.Session.request')
    def test_create_text_post_api_error(self, mock_request, facebook_manager):
        """Test text post creation with API error"""
        # Mock error response
        mock_response = Mock()
        mock_response.json.return_value = {
            'error': {
                'code': 100,
                'message': 'Invalid parameter',
                'type': 'GraphMethodException'
            }
        }
        mock_request.return_value = mock_response
        
        post_request = TextPostRequest(message="Test post")
        
        with pytest.raises(PostCreationError) as exc_info:
            facebook_manager.create_text_post(post_request)
        
        assert "Invalid parameter" in str(exc_info.value)
    
    @patch('src.facebook_manager.requests.Session.request')
    def test_create_text_post_no_post_id(self, mock_request, facebook_manager):
        """Test text post creation when no post ID is returned"""
        # Mock response without post ID
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response
        
        post_request = TextPostRequest(message="Test post")
        
        with pytest.raises(PostCreationError) as exc_info:
            facebook_manager.create_text_post(post_request)
        
        assert "No post ID returned" in str(exc_info.value)


class TestCreateImagePost:
    """Test image post creation"""
    
    @patch('src.facebook_manager.requests.Session.request')
    def test_create_image_post_from_url_success(self, mock_request, facebook_manager):
        """Test successful image post creation from URL"""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            'id': '123456789_987654321',
            'post_id': '123456789_987654321'
        }
        mock_request.return_value = mock_response
        
        post_request = ImagePostRequest(
            message="Check this out!",
            image_url="https://example.com/image.jpg"
        )
        response = facebook_manager.create_image_post(post_request)
        
        assert isinstance(response, FacebookPostResponse)
        assert response.post_id == '123456789_987654321'
        assert response.success is True
        
        # Verify the API was called correctly
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[1]['method'] == 'POST'
        assert '123456789/photos' in call_args[1]['url']
        assert call_args[1]['data']['message'] == "Check this out!"
        assert 'https://example.com/image.jpg' in call_args[1]['data']['url']
    
    @patch('src.facebook_manager.requests.Session.request')
    def test_create_image_post_from_url_without_message(self, mock_request, facebook_manager):
        """Test image post creation from URL without message"""
        mock_response = Mock()
        mock_response.json.return_value = {'id': '123456789_987654321'}
        mock_request.return_value = mock_response
        
        post_request = ImagePostRequest(image_url="https://example.com/image.jpg")
        response = facebook_manager.create_image_post(post_request)
        
        assert response.post_id == '123456789_987654321'
        
        # Verify message was not included in request
        call_args = mock_request.call_args
        assert 'message' not in call_args[1]['data']
    
    @patch('builtins.open', new_callable=mock_open, read_data=b'fake image data')
    @patch('pathlib.Path.exists')
    @patch('src.facebook_manager.requests.Session.request')
    def test_create_image_post_from_file_success(
        self, mock_request, mock_exists, mock_file, facebook_manager
    ):
        """Test successful image post creation from file"""
        # Mock file exists
        mock_exists.return_value = True
        
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {'id': '123456789_987654321'}
        mock_request.return_value = mock_response
        
        post_request = ImagePostRequest(
            message="Local image",
            image_path="/path/to/image.jpg"
        )
        response = facebook_manager.create_image_post(post_request)
        
        assert isinstance(response, FacebookPostResponse)
        assert response.post_id == '123456789_987654321'
        assert response.success is True
        
        # Verify file was opened
        mock_file.assert_called_once()
    
    @patch('pathlib.Path.exists')
    def test_create_image_post_file_not_found(self, mock_exists, facebook_manager):
        """Test image post creation when file doesn't exist"""
        mock_exists.return_value = False
        
        post_request = ImagePostRequest(
            message="Test",
            image_path="/nonexistent/image.jpg"
        )
        
        with pytest.raises(ImageUploadError) as exc_info:
            facebook_manager.create_image_post(post_request)
        
        assert "not found" in str(exc_info.value)
    
    @patch('pathlib.Path.exists')
    def test_create_image_post_invalid_format(self, mock_exists, facebook_manager):
        """Test image post creation with invalid file format"""
        mock_exists.return_value = True
        
        post_request = ImagePostRequest(
            message="Test",
            image_path="/path/to/file.txt"
        )
        
        with pytest.raises(ImageUploadError) as exc_info:
            facebook_manager.create_image_post(post_request)
        
        assert "Invalid image format" in str(exc_info.value)


class TestVerifyCredentials:
    """Test credential verification"""
    
    @patch('src.facebook_manager.requests.Session.request')
    def test_verify_credentials_success(self, mock_request, facebook_manager):
        """Test successful credential verification"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'id': '123456789',
            'name': 'Test Page'
        }
        mock_request.return_value = mock_response
        
        result = facebook_manager.verify_credentials()
        
        assert result is True
        
        # Verify the API was called correctly
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[1]['method'] == 'GET'
        assert '123456789' in call_args[1]['url']
    
    @patch('src.facebook_manager.requests.Session.request')
    def test_verify_credentials_invalid(self, mock_request, facebook_manager):
        """Test credential verification with invalid credentials"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'error': {
                'code': 190,
                'message': 'Invalid OAuth access token',
                'type': 'OAuthException'
            }
        }
        mock_request.return_value = mock_response
        
        with pytest.raises(InvalidCredentialsError) as exc_info:
            facebook_manager.verify_credentials()
        
        assert "Invalid" in str(exc_info.value)


class TestGetPost:
    """Test retrieving post details"""
    
    @patch('src.facebook_manager.requests.Session.request')
    def test_get_post_success(self, mock_request, facebook_manager):
        """Test successful post retrieval"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'id': '123456789_987654321',
            'message': 'Test post',
            'created_time': '2025-01-01T00:00:00+0000',
            'permalink_url': 'https://facebook.com/123456789/posts/987654321'
        }
        mock_request.return_value = mock_response
        
        post_data = facebook_manager.get_post('123456789_987654321')
        
        assert post_data['id'] == '123456789_987654321'
        assert post_data['message'] == 'Test post'
        assert 'created_time' in post_data
        assert 'permalink_url' in post_data


class TestMimeTypeDetection:
    """Test MIME type detection for images"""
    
    def test_get_mime_type_jpg(self, facebook_manager):
        """Test MIME type for JPG files"""
        mime_type = facebook_manager._get_mime_type(Path('image.jpg'))
        assert mime_type == 'image/jpeg'
    
    def test_get_mime_type_png(self, facebook_manager):
        """Test MIME type for PNG files"""
        mime_type = facebook_manager._get_mime_type(Path('image.png'))
        assert mime_type == 'image/png'
    
    def test_get_mime_type_gif(self, facebook_manager):
        """Test MIME type for GIF files"""
        mime_type = facebook_manager._get_mime_type(Path('image.gif'))
        assert mime_type == 'image/gif'
    
    def test_get_mime_type_unknown(self, facebook_manager):
        """Test MIME type for unknown file type"""
        mime_type = facebook_manager._get_mime_type(Path('file.xyz'))
        assert mime_type == 'application/octet-stream'


class TestErrorHandling:
    """Test error handling scenarios"""
    
    @patch('src.facebook_manager.requests.Session.request')
    def test_authentication_error(self, mock_request, facebook_manager):
        """Test handling of authentication errors"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'error': {
                'code': 190,
                'message': 'Invalid OAuth access token',
                'type': 'OAuthException'
            }
        }
        mock_request.return_value = mock_response
        
        post_request = TextPostRequest(message="Test")
        
        with pytest.raises(PostCreationError) as exc_info:
            facebook_manager.create_text_post(post_request)
        
        # Should contain InvalidCredentialsError message
        assert "Invalid" in str(exc_info.value).lower() or "oauth" in str(exc_info.value).lower()
    
    @patch('src.facebook_manager.requests.Session.request')
    def test_timeout_error(self, mock_request, facebook_manager):
        """Test handling of timeout errors"""
        import requests
        mock_request.side_effect = requests.exceptions.Timeout("Request timed out")
        
        post_request = TextPostRequest(message="Test")
        
        with pytest.raises(PostCreationError) as exc_info:
            facebook_manager.create_text_post(post_request)
        
        assert "timeout" in str(exc_info.value).lower()
    
    @patch('src.facebook_manager.requests.Session.request')
    def test_connection_error(self, mock_request, facebook_manager):
        """Test handling of connection errors"""
        import requests
        mock_request.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        post_request = TextPostRequest(message="Test")
        
        with pytest.raises(PostCreationError) as exc_info:
            facebook_manager.create_text_post(post_request)
        
        assert "failed" in str(exc_info.value).lower()
