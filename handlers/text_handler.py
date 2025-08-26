"""
Text message handler for processing text messages and user registration.
"""
from handlers.base_handler import BaseHandler
from interfaces.handlers import ITextMessageHandler
from utils.message_utils import (
    handle_rich_menu, send_text_message, send_message, 
    text_message, info_hint_message
)
from utils.file_utils import user_data_enter
from constants import ERROR_MESSAGES


class TextHandler(BaseHandler, ITextMessageHandler):
    """Handler for text message events."""
    
    async def handle(self, event) -> bool:
        """
        Handle text message event.
        
        Args:
            event: The text message event
            
        Returns:
            True if handled successfully, False otherwise
        """
        user_id = event.source.user_id
        message = event.message.text.strip()
        
        await handle_rich_menu(user_id)
        
        # Check if user is in registration process
        if user_id in user_data_enter:
            return await self._handle_registration(event, message)
        
        # Check if user is logged in for other operations
        if not await self.check_user_login(event):
            return False
        
        # Handle other text message logic here
        return True
    
    async def _handle_registration(self, event, message: str) -> bool:
        """
        Handle user registration process.
        
        Args:
            event: The text message event
            message: The user's message text
            
        Returns:
            True if handled successfully, False otherwise
        """
        user_id = event.source.user_id
        info = user_data_enter[user_id]
        
        try:
            # Class time selection (step 0)
            if len(info) == 0:
                if not message.isdigit():
                    await send_text_message(event, ERROR_MESSAGES['student_id_format_error'])
                    return False
                # Add class time to info and continue
                info.append(int(message))
                
            # Department (step 1)
            elif len(info) == 1:
                info.append(message)
                
            # Student ID validation (step 2)
            elif len(info) == 2:
                is_valid, error_msg = self.user_service.validate_student_id(message)
                if not is_valid:
                    await send_text_message(event, error_msg)
                    return False
                info.append(message)
                
            # Name (final step)
            else:
                info.append(message)
                # Complete registration
                return await self._complete_registration(event, info)
            
            # Continue registration process
            user_data_enter[user_id] = info
            await send_message(event, await info_hint_message(len(info)))
            return True
            
        except Exception as e:
            print(f"Error in registration: {e}")
            await self.send_error_message(event, 'processing_error')
            return False
    
    async def _complete_registration(self, event, info: list) -> bool:
        """
        Complete the user registration process.
        
        Args:
            event: The text message event
            info: Registration information [class_time, department, student_id, name]
            
        Returns:
            True if registration completed successfully, False otherwise
        """
        try:
            user_id = event.source.user_id
            class_time, department, student_id, name = info
            
            # Create user
            user = self.user_service.create_user(
                user_id=user_id,
                class_time=class_time,
                department=department,
                student_id=student_id,
                name=name
            )
            
            # Clean up registration data
            del user_data_enter[user_id]
            
            # Send success message
            success_message = self.user_service.get_registration_success_message(name)
            await send_message(event, [await text_message(success_message)])
            
            return True
            
        except Exception as e:
            print(f"Error completing registration: {e}")
            await self.send_error_message(event, 'processing_error')
            return False