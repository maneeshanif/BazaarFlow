"""
Unit tests for Pydantic models
"""

import pytest
from pydantic import ValidationError

from src.models import (
    TextPostRequest,
    ImagePostRequest,
    VideoPostRequest,
    FacebookPostResponse,
    FacebookErrorResponse,
    PostType,
    PageInfo
)


class TestTextPostRequest:
    """Test cases for TextPostRequest model"""
    
    def test_valid_text_post(self):
        """Test creating a valid text post request"""
        post = TextPostRequest(message="Hello, world!")
        assert post.message == "Hello, world!"
    
    def test_text_post_strips_whitespace(self):
        """Test that whitespace is stripped from message"""
        post = TextPostRequest(message="  Hello, world!  ")
        assert post.message == "Hello, world!"
    
    def test_empty_message_raises_error(self):
        """Test that empty message raises validation error"""
        with pytest.raises(ValidationError) as exc_info:
            TextPostRequest(message="")
        
        assert "Message cannot be empty" in str(exc_info.value)
    
    def test_whitespace_only_message_raises_error(self):
        """Test that whitespace-only message raises validation error"""
        with pytest.raises(ValidationError) as exc_info:
            TextPostRequest(message="   ")
        
        assert "Message cannot be empty" in str(exc_info.value)
    
    def test_message_too_long(self):
        """Test that message exceeding max length raises error"""
        long_message = "a" * 63207
        with pytest.raises(ValidationError) as exc_info:
            TextPostRequest(message=long_message)
        
        assert "at most 63206 characters" in str(exc_info.value).lower()
    
    def test_missing_message_raises_error(self):
        """Test that missing message raises validation error"""
        with pytest.raises(ValidationError):
            TextPostRequest()


class TestImagePostRequest:
    """Test cases for ImagePostRequest model"""
    
    def test_valid_image_url_post(self):
        """Test creating a valid image post with URL"""
        post = ImagePostRequest(
            message="Check this out!",
            image_url="https://example.com/image.jpg"
        )
        assert post.message == "Check this out!"
        assert str(post.image_url) == "https://example.com/image.jpg/"
    
    def test_valid_image_path_post(self):
        """Test creating a valid image post with file path"""
        post = ImagePostRequest(
            message="Local image",
            image_path="/path/to/image.jpg"
        )
        assert post.message == "Local image"
        assert post.image_path == "/path/to/image.jpg"
    
    def test_image_post_without_message(self):
        """Test creating image post without message"""
        post = ImagePostRequest(image_url="https://example.com/image.jpg")
        assert post.message is None
        assert post.image_url is not None
    
    def test_no_image_source_raises_error(self):
        """Test that missing both image_url and image_path raises error"""
        with pytest.raises(ValidationError) as exc_info:
            ImagePostRequest(message="Test")
        
        assert "Either image_url or image_path must be provided" in str(exc_info.value)
    
    def test_both_image_sources_raises_error(self):
        """Test that providing both image_url and image_path raises error"""
        with pytest.raises(ValidationError) as exc_info:
            ImagePostRequest(
                message="Test",
                image_url="https://example.com/image.jpg",
                image_path="/path/to/image.jpg"
            )
        
        assert "Only one of image_url or image_path should be provided" in str(exc_info.value)
    
    def test_invalid_url_raises_error(self):
        """Test that invalid URL raises validation error"""
        with pytest.raises(ValidationError):
            ImagePostRequest(
                message="Test",
                image_url="not-a-valid-url"
            )
    
    def test_message_whitespace_handling(self):
        """Test that whitespace in message is handled correctly"""
        post = ImagePostRequest(
            message="  Test message  ",
            image_url="https://example.com/image.jpg"
        )
        assert post.message == "Test message"


class TestVideoPostRequest:
    """Test cases for VideoPostRequest model"""
    
    def test_valid_video_url_post(self):
        """Test creating a valid video post with URL"""
        post = VideoPostRequest(
            message="Watch this!",
            video_url="https://example.com/video.mp4"
        )
        assert post.message == "Watch this!"
        assert str(post.video_url) == "https://example.com/video.mp4"
    
    def test_valid_video_path_post(self):
        """Test creating a valid video post with file path"""
        post = VideoPostRequest(
            message="Local video",
            video_path="/path/to/video.mp4"
        )
        assert post.message == "Local video"
        assert post.video_path == "/path/to/video.mp4"
    
    def test_no_video_source_raises_error(self):
        """Test that missing both video_url and video_path raises error"""
        with pytest.raises(ValidationError) as exc_info:
            VideoPostRequest(message="Test")
        
        assert "Either video_url or video_path must be provided" in str(exc_info.value)


class TestFacebookPostResponse:
    """Test cases for FacebookPostResponse model"""
    
    def test_valid_response(self):
        """Test creating a valid response"""
        response = FacebookPostResponse(
            post_id="123456789_987654321",
            success=True,
            message="Post created successfully"
        )
        assert response.post_id == "123456789_987654321"
        assert response.success is True
        assert response.message == "Post created successfully"
    
    def test_minimal_response(self):
        """Test creating response with only required fields"""
        response = FacebookPostResponse(post_id="123456789")
        assert response.post_id == "123456789"
        assert response.success is True
        assert response.message is None


class TestFacebookErrorResponse:
    """Test cases for FacebookErrorResponse model"""
    
    def test_valid_error_response(self):
        """Test creating a valid error response"""
        error = FacebookErrorResponse(
            error_code=190,
            error_message="Invalid OAuth access token",
            error_type="OAuthException",
            error_subcode=460
        )
        assert error.error_code == 190
        assert error.error_message == "Invalid OAuth access token"
        assert error.error_type == "OAuthException"
        assert error.error_subcode == 460
    
    def test_error_without_subcode(self):
        """Test creating error response without subcode"""
        error = FacebookErrorResponse(
            error_code=100,
            error_message="Invalid parameter",
            error_type="GraphMethodException"
        )
        assert error.error_subcode is None


class TestPageInfo:
    """Test cases for PageInfo model"""
    
    def test_valid_page_info(self):
        """Test creating valid page info"""
        page = PageInfo(
            page_id="123456789",
            page_name="Test Page",
            access_token="EAAtest123"
        )
        assert page.page_id == "123456789"
        assert page.page_name == "Test Page"
        assert page.access_token == "EAAtest123"
    
    def test_page_info_without_name(self):
        """Test creating page info without name"""
        page = PageInfo(
            page_id="123456789",
            access_token="EAAtest123"
        )
        assert page.page_name is None


class TestPostType:
    """Test cases for PostType enum"""
    
    def test_post_type_values(self):
        """Test that all post types have correct values"""
        assert PostType.TEXT == "text"
        assert PostType.TEXT_WITH_IMAGE == "text_with_image"
        assert PostType.IMAGE == "image"
        assert PostType.VIDEO == "video"
        assert PostType.VIDEO_WITH_TEXT == "video_with_text"
