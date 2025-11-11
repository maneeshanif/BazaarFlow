"""Unit tests for the chat service."""
from types import SimpleNamespace

import pytest
from services.chat_service import ChatService, chat_service
from agents import SQLiteSession, Runner


@pytest.fixture(autouse=True)
def stub_runner(monkeypatch):
    async def _fake_run(*args, **kwargs):
        return SimpleNamespace(final_output="stub response")

    monkeypatch.setattr(Runner, "run", _fake_run)


@pytest.fixture
def chat_service_instance():
    """Create a fresh chat service instance for each test"""
    service = ChatService()
    return service


@pytest.mark.asyncio
async def test_process_message_new_session(chat_service_instance):
    """Test processing a message with a new session"""
    response_text, session_id = await chat_service_instance.process_message(
        message="Hello, what can you do?",
        session_id=None
    )
    
    assert isinstance(response_text, str)
    assert isinstance(session_id, str)
    assert session_id.startswith("web_")
    assert response_text == "stub response"


@pytest.mark.asyncio
async def test_process_message_existing_session(chat_service_instance):
    """Test processing a message with an existing session ID"""
    test_session_id = "test_session_123"
    response_text, returned_session_id = await chat_service_instance.process_message(
        message="Hello from existing session",
        session_id=test_session_id
    )
    
    assert returned_session_id == test_session_id
    assert isinstance(response_text, str)
    assert response_text == "stub response"
    
    # Verify the session was created
    session = chat_service_instance.get_session(test_session_id)
    assert session is not None


@pytest.mark.asyncio
async def test_process_message_error_handling(chat_service_instance):
    """Test error handling in message processing"""
    # This test may require mocking the agent to simulate an error
    # For now, test with various inputs to ensure no exceptions
    test_messages = [
        "",
        "   ",
        "!",
        "?",
        "This is a test message",
        "Hello! What's up?",
        "12345",
        "Test with unicode: café, résumé, naïve",
    ]
    
    for msg in test_messages:
        response_text, session_id = await chat_service_instance.process_message(
            message=msg,
            session_id=None
        )
        
        assert isinstance(response_text, str)
        assert isinstance(session_id, str)
        assert len(session_id) > 0


def test_get_session_nonexistent(chat_service_instance):
    """Test getting a session that doesn't exist"""
    session = chat_service_instance.get_session("nonexistent_session")
    assert session is None


def test_create_session(chat_service_instance):
    """Test creating a new session"""
    session_id = "new_session_test"
    session = chat_service_instance.create_session(session_id)
    
    assert session is not None
    assert isinstance(session, SQLiteSession)
    
    # Verify the session can be retrieved
    retrieved_session = chat_service_instance.get_session(session_id)
    assert retrieved_session is not None
    assert retrieved_session == session


def test_singleton_service():
    """Test that the global chat service exists and works"""
    assert chat_service is not None
    assert isinstance(chat_service, ChatService)


@pytest.mark.asyncio
async def test_session_persistence_in_service():
    """Test that sessions persist within the service"""
    service = ChatService()
    session_id = "persistence_test"
    
    # First message creates the session
    _, returned_id = await service.process_message(
        message="First message",
        session_id=session_id
    )
    
    assert returned_id == session_id
    
    # Verify the session exists in the service
    session = service.get_session(session_id)
    assert session is not None
    
    # Second message uses the same session
    _, next_returned_id = await service.process_message(
        message="Second message",
        session_id=session_id
    )
    
    assert next_returned_id == session_id
    
    # Session should still exist after both messages
    final_session = service.get_session(session_id)
    assert final_session is not None