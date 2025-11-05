"""
Pytest configuration and shared fixtures
"""

import pytest
import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))


@pytest.fixture(autouse=True)
def reset_config_singleton():
    """Reset the config singleton before each test"""
    from src import config as config_module
    config_module._config_instance = None
    yield
    config_module._config_instance = None


@pytest.fixture
def sample_text_post():
    """Sample text post data"""
    return {
        "message": "This is a test post from the Facebook Manager Tool!"
    }


@pytest.fixture
def sample_image_url():
    """Sample image URL"""
    return "https://picsum.photos/800/600"


@pytest.fixture
def sample_image_post_url():
    """Sample image post with URL"""
    return {
        "message": "Check out this amazing image!",
        "image_url": "https://picsum.photos/800/600"
    }
