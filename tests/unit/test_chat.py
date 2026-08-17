"""
Tests for the chat controller
"""
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from controllers.chat_controller import router
from services.chat_service import chat_service

# Create a test FastAPI app
app = FastAPI()
app.include_router(router)

client = TestClient(app)

def test_chat_sales_endpoint():
    """Test the chat/sales endpoint"""
    response = client.post("/chat/sales", json={
        "message": "Hello, what products do you have?"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "session_id" in data
    assert isinstance(data["response"], str)
    assert isinstance(data["session_id"], str)
    assert data["session_id"].startswith("web_")

def test_chat_sales_endpoint_with_session():
    """Test the chat/sales endpoint with a provided session ID"""
    session_id = "test_session_123"
    response = client.post("/chat/sales", json={
        "message": "Hello, what products do you have?",
        "session_id": session_id
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id

def test_chat_sales_endpoint_empty_message():
    """Test the chat/sales endpoint with empty message"""
    response = client.post("/chat/sales", json={
        "message": ""
    })
    
    assert response.status_code == 200  # Should still return a response even with empty message

def test_chat_sales_endpoint_special_characters():
    """Test the chat/sales endpoint with special characters"""
    response = client.post("/chat/sales", json={
        "message": "Hello! What's the price of iPhone 15? 📱",
        "session_id": "test_special_chars"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert isinstance(data["response"], str)

def test_health_endpoint():
    """Test the health endpoint"""
    response = client.get("/health/chat")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "chat service is running"}

def test_chat_service_initialization():
    """Test that the chat service is properly initialized"""
    assert chat_service is not None
    assert hasattr(chat_service, 'process_message')
    assert hasattr(chat_service, 'get_session')
    assert hasattr(chat_service, 'create_session')

@pytest.mark.asyncio
async def test_chat_service_process_message():
    """Test the chat service directly"""
    response_text, session_id = await chat_service.process_message(
        message="What products do you have?",
        session_id=None
    )
    
    assert isinstance(response_text, str)
    assert isinstance(session_id, str)
    assert session_id.startswith("web_")

@pytest.mark.asyncio
async def test_chat_service_with_existing_session():
    """Test the chat service with an existing session"""
    # Create a session first
    session_id = "test_existing_session"
    response_text, returned_session_id = await chat_service.process_message(
        message="Hello, I'm a new customer",
        session_id=session_id
    )
    
    assert returned_session_id == session_id
    assert isinstance(response_text, str)
    
    # Now try with same session ID to continue conversation
    next_response_text, next_session_id = await chat_service.process_message(
        message="Can you show me some products?",
        session_id=session_id
    )
    
    assert next_session_id == session_id
    assert isinstance(next_response_text, str)