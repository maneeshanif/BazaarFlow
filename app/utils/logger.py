"""
Logger utility for BazaarFlow backend.
Provides centralized logging configuration and custom formatters.
"""
import logging
import os
from typing import Optional

def setup_logger(name: str = None) -> logging.Logger:
    """
    Configure and return a logger with consistent formatting and level.
    
    Args:
        name: Optional name for the logger. Defaults to __name__
    
    Returns:
        logging.Logger: Configured logger instance
    """
    # Get or create logger
    logger = logging.getLogger(name or __name__)
    
    # Only configure if it hasn't been configured yet
    if not logger.handlers:
        logger.setLevel(logging.DEBUG if os.getenv("DEBUG") else logging.INFO)
        
        # Console handler with custom formatting
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Configure related loggers for debugging
        if os.getenv("DEBUG"):
            logging.getLogger('pywa_async').setLevel(logging.DEBUG)
            logging.getLogger('httpx').setLevel(logging.DEBUG)
    
    return logger

def log_webhook_event(logger: logging.Logger, event_type: str, details: Optional[dict] = None):
    """
    Log webhook related events with consistent formatting.
    
    Args:
        logger: Logger instance to use
        event_type: Type of webhook event (e.g., "received", "processed", "error")
        details: Optional dictionary of event details to log
    """
    details = details or {}
    logger.info(f"[WhatsApp Webhook] {event_type} | {details}")

def log_message_event(logger: logging.Logger, event_type: str, user_id: str, details: Optional[dict] = None):
    """
    Log message handling events with consistent formatting.
    
    Args:
        logger: Logger instance to use
        event_type: Type of message event (e.g., "received", "processed", "error")
        user_id: WhatsApp user ID associated with the message
        details: Optional dictionary of message details to log
    """
    details = details or {}
    logger.info(f"[WhatsApp Message] {event_type} | User: {user_id} | {details}")