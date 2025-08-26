"""
Base handler class providing common functionality for all handlers.
"""
from abc import ABC, abstractmethod
from typing import Any

from interfaces.handlers import IEventHandler
from interfaces.services import IAudioService, IAssessmentService, IUserService
from services.container import container
from utils.message_utils import send_text_message
from constants import ERROR_MESSAGES


class BaseHandler(IEventHandler):
    """Abstract base class for all event handlers."""
    
    def __init__(self) -> None:
        self.user_service: IUserService = container.get_user_service()
        self.audio_service: IAudioService = container.get_audio_service()
        self.assessment_service: IAssessmentService = container.get_assessment_service()
    
    @abstractmethod
    async def handle(self, event: Any) -> bool:
        """
        Handle the event.
        
        Args:
            event: The event to handle
            
        Returns:
            True if handled successfully, False otherwise
        """
        pass
    
    async def check_user_login(self, event: Any) -> bool:
        """
        Check if user is logged in and send error message if not.
        
        Args:
            event: The event containing user information
            
        Returns:
            True if user is logged in, False otherwise
        """
        user_id = event.source.user_id
        if not self.user_service.is_user_logged_in(user_id):
            await send_text_message(event, ERROR_MESSAGES['login_required'])
            return False
        return True
    
    async def send_error_message(self, event: Any, error_key: str) -> None:
        """
        Send a standardized error message.
        
        Args:
            event: The event to respond to
            error_key: The error message key from ERROR_MESSAGES
        """
        await send_text_message(event, ERROR_MESSAGES.get(error_key, ERROR_MESSAGES['processing_error']))