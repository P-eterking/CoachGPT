"""
Audio message handler for processing voice messages and speech assessment.
"""
import time
from typing import Optional

from handlers.base_handler import BaseHandler
from interfaces.handlers import IAudioMessageHandler
from utils.message_utils import (
    handle_rich_menu, show_loading, send_text_message, 
    send_message, result_message, handle_chat
)
from utils.file_utils import isEnabled, addHistory
from config import app_config
from constants import (
    AUDIO_LOADING_TIMEOUT, CHAT_ENABLED_CATEGORIES, 
    ERROR_MESSAGES, MIN_TEXT_LENGTH
)


class AudioHandler(BaseHandler, IAudioMessageHandler):
    """Handler for audio message events."""
    
    async def handle(self, event) -> bool:
        """
        Handle audio message event.
        
        Args:
            event: The audio message event
            
        Returns:
            True if handled successfully, False otherwise
        """
        # Check user login status
        if not await self.check_user_login(event):
            return False
        
        user_id = event.source.user_id
        await handle_rich_menu(user_id)
        
        user_state = self.user_service.get_user_state(user_id)
        if not user_state:
            return False
        
        await show_loading(user_id, secs=AUDIO_LOADING_TIMEOUT)
        
        try:
            # Handle chat categories
            if await self._handle_chat_categories(event, user_state):
                return True
            
            # Handle assessment categories
            return await self._handle_assessment_categories(event, user_state)
            
        except Exception as e:
            print(f"Error in audio handler: {e}")
            await self.send_error_message(event, 'processing_error')
            return False
    
    async def _handle_chat_categories(self, event, user_state) -> bool:
        """
        Handle chat-enabled categories.
        
        Args:
            event: The audio message event
            user_state: Current user state
            
        Returns:
            True if this was a chat category, False otherwise
        """
        category = user_state.category
        
        if category in CHAT_ENABLED_CATEGORIES:
            if not isEnabled('chat'):
                await self.send_error_message(event, 'unit_unavailable')
                return True
            
            await handle_chat(event)
            return True
        
        return False
    
    async def _handle_assessment_categories(self, event, user_state) -> bool:
        """
        Handle assessment categories.
        
        Args:
            event: The audio message event
            user_state: Current user state
            
        Returns:
            True if handled successfully, False otherwise
        """
        category = user_state.category
        
        if not category or not app_config.question_manager.has_question(category):
            return False
        
        sub = user_state.sub
        if sub == -1:
            await self.send_error_message(event, 'select_unit')
            return False
        
        # Get question
        question = app_config.question_manager.get_question(category, sub)
        if not question:
            return False
        
        # Process audio
        transcribed_text = await self._process_audio(event)
        if not transcribed_text:
            return False
        
        # Assess speech
        assessment = await self.assessment_service.assess_speech(question, transcribed_text)
        if not assessment or not self.assessment_service.validate_assessment(assessment):
            await self.send_error_message(event, 'processing_error')
            return False
        
        # Save assessment and send response
        return await self._save_and_respond(event, user_state, assessment)
    
    async def _process_audio(self, event) -> Optional[str]:
        """
        Process audio message and return transcribed text.
        
        Args:
            event: The audio message event
            
        Returns:
            Transcribed text or None if failed
        """
        try:
            # Get audio content
            message_content = await self.audio_service.get_audio_content(event.message.id)
            if not message_content:
                await self.send_error_message(event, 'audio_content_failed')
                return None
            
            # Transcribe audio
            text = await self.audio_service.transcribe_audio(message_content, language="en")
            if not text or len(text) < MIN_TEXT_LENGTH:
                await self.send_error_message(event, 'audio_content_failed')
                print('No text found in audio')
                return None
            
            return text
            
        except Exception as e:
            print(f"Error processing audio: {e}")
            await self.send_error_message(event, 'transcription_failed')
            return None
    
    async def _save_and_respond(self, event, user_state, assessment) -> bool:
        """
        Save assessment to history and send response to user.
        
        Args:
            event: The audio message event
            user_state: Current user state
            assessment: The speech assessment result
            
        Returns:
            True if successful, False otherwise
        """
        try:
            user_id = event.source.user_id
            category = user_state.category
            sub = user_state.sub
            
            # Add timestamp
            assessment.timestamp = time.time()
            
            # Save to history
            history_key = f"{category}-{sub}"
            addHistory(user_id, history_key, assessment)
            
            # Send result message
            await send_message(event, await result_message(assessment))
            
            return True
            
        except Exception as e:
            print(f"Error saving assessment: {e}")
            await self.send_error_message(event, 'processing_error')
            return False