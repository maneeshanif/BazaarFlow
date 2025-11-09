"""
Chat Service for handling sales agent conversations
This service manages chat sessions and processes messages using the sales agent.
"""
from typing import Optional
import logging
from agents import Runner, SQLiteSession
from my_agents.sales_agent import sales_agent

logger = logging.getLogger(__name__)

class ChatService:
    """
    Service class for handling chat conversations with the sales agent
    """
    
    def __init__(self):
        # In-memory store for active sessions
        # In production, you'd likely use Redis or a database
        self.active_sessions = {}
    
    async def process_message(self, message: str, session_id: Optional[str]) -> tuple[str, str]:
        """
        Process a user message through the sales agent
        
        Args:
            message: The user's message
            session_id: Optional session ID to maintain conversation context
            
        Returns:
            Tuple of (response_text, session_id)
        """
        try:
            # Use provided session_id or generate a new one
            if not session_id:
                session_id = f"web_{len(self.active_sessions) + 1}"
            
            # Get or create session for conversation history
            if session_id not in self.active_sessions:
                session = SQLiteSession(session_id=session_id)
                self.active_sessions[session_id] = session
            else:
                session = self.active_sessions[session_id]
            
            # Run the sales agent with the user's message
            response = await Runner.run(
                starting_agent=sales_agent,
                input=message,
                session=session
            )
            
            # Get the final output from the agent
            response_text = response.final_output if hasattr(response, 'final_output') else str(response)
            
            return response_text, session_id
            
        except Exception as e:
            logger.error(f"Error processing message in session {session_id}: {str(e)}")
            return "Sorry, I encountered an error processing your request. Please try again.", session_id

    def get_session(self, session_id: str) -> Optional[SQLiteSession]:
        """
        Get a session by ID
        """
        return self.active_sessions.get(session_id)
    
    def create_session(self, session_id: str) -> SQLiteSession:
        """
        Create a new session
        """
        session = SQLiteSession(session_id=session_id)
        self.active_sessions[session_id] = session
        return session

# Create a singleton instance of the service
chat_service = ChatService()