"""
Postback handler for processing user interactions with buttons and rich menus.
"""
from handlers.base_handler import BaseHandler
from interfaces.handlers import IPostbackHandler
from utils.message_utils import handle_rich_menu, send_message, question_message
from utils.file_utils import getData
from config import app_config


class PostbackHandler(BaseHandler, IPostbackHandler):
    """Handler for postback events."""
    
    async def handle(self, event) -> bool:
        """
        Handle postback event.
        
        Args:
            event: The postback event
            
        Returns:
            True if handled successfully, False otherwise
        """
        # Check user login status
        if not await self.check_user_login(event):
            return False
        
        user_id = event.source.user_id
        await handle_rich_menu(user_id)
        
        try:
            postback_data = event.postback.data
            return await self._process_postback_data(event, postback_data)
            
        except Exception as e:
            print(f"Error in postback handler: {e}")
            await self.send_error_message(event, 'processing_error')
            return False
    
    async def _process_postback_data(self, event, postback_data: str) -> bool:
        """
        Process postback data and route to appropriate handler.
        
        Args:
            event: The postback event
            postback_data: The postback data string
            
        Returns:
            True if handled successfully, False otherwise
        """
        user_id = event.source.user_id
        user_state = self.user_service.get_user_state(user_id)
        
        # Parse postback data (assuming format like "category:action" or "category:sub:action")
        parts = postback_data.split(':')
        
        if len(parts) >= 2:
            category = parts[0]
            action = parts[1]
            
            if action == 'select':
                # Category selection
                user_state.category = category
                user_state.sub = -1  # Reset sub selection
                return True
                
            elif action == 'unit' and len(parts) >= 3:
                # Unit/sub selection
                try:
                    sub_index = int(parts[2])
                    user_state.sub = sub_index
                    
                    # Send question if available
                    if app_config.question_manager.has_question(category):
                        question = app_config.question_manager.get_question(category, sub_index)
                        if question:
                            await send_message(event, await question_message(question))
                    
                    return True
                except ValueError:
                    return False
        
        return False