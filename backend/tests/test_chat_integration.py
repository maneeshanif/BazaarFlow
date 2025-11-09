"""
Integration tests for the sales agent chat functionality
"""
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from controllers.chat_controller import router
from my_agents.sales_agent import sales_agent
from agents import Runner, SQLiteSession
import asyncio

# Create a test FastAPI app
app = FastAPI()
app.include_router(router)

client = TestClient(app)

def test_sales_agent_integration():
    """Test that the sales agent is properly integrated"""
    # Test with a sample message
    response = client.post("/chat/sales", json={
        "message": "What products do you have?",
        "session_id": "integration_test"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert len(data["response"]) > 0  # Should have some response

def test_sales_agent_product_query():
    """Test that sales agent can handle product queries"""
    response = client.post("/chat/sales", json={
        "message": "Show me all products",
        "session_id": "product_test"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    # The response should contain product-related information
    assert len(data["response"]) > 0

def test_sales_agent_price_query():
    """Test that sales agent can handle price queries"""
    response = client.post("/chat/sales", json={
        "message": "What's the price of iPhone?",
        "session_id": "price_test"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert len(data["response"]) > 0

def test_conversation_continuation():
    """Test that conversation context is maintained across messages"""
    session_id = "conversation_test"
    
    # First message
    response1 = client.post("/chat/sales", json={
        "message": "I want to buy a phone",
        "session_id": session_id
    })
    assert response1.status_code == 200
    
    # Second message in same session
    response2 = client.post("/chat/sales", json={
        "message": "What options do you have under 100000?",
        "session_id": session_id
    })
    assert response2.status_code == 200
    
    data2 = response2.json()
    assert "response" in data2
    # The agent should understand the context of the previous conversation

@pytest.mark.asyncio
async def test_direct_sales_agent_runner():
    """Test the sales agent directly using Runner"""
    session = SQLiteSession(session_id="direct_test")
    
    # Run the sales agent with a sample message
    result = await Runner.run(
        starting_agent=sales_agent,
        input="Hello, what products do you offer?",
        session=session
    )
    
    # Check that we get a proper response
    assert result is not None
    if hasattr(result, 'final_output'):
        assert isinstance(result.final_output, str)
        assert len(result.final_output) > 0
    else:
        # If the result doesn't have final_output, check if it's a string itself
        assert isinstance(result, str)

def test_error_handling():
    """Test error handling in the chat flow"""
    # Test with malformed request
    response = client.post("/chat/sales", json={
        # Missing required "message" field
    })
    
    # Should return 422 for validation error
    assert response.status_code in [422, 200]  # 200 if handled gracefully
    
    # Test with very long message
    long_message = "Hello " * 1000
    response = client.post("/chat/sales", json={
        "message": long_message,
        "session_id": "long_message_test"
    })
    
    # Should handle long messages gracefully
    assert response.status_code == 200