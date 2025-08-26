"""
Handler interfaces for defining event handler contracts.
"""
from abc import ABC, abstractmethod
from typing import Any


class IEventHandler(ABC):
    """Interface for event handlers."""
    
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


class ITextMessageHandler(IEventHandler):
    """Interface for text message handlers."""
    pass


class IAudioMessageHandler(IEventHandler):
    """Interface for audio message handlers."""
    pass


class IPostbackHandler(IEventHandler):
    """Interface for postback handlers."""
    pass