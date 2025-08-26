"""Refactored handlers using service-oriented architecture."""

from typing import Optional
from linebot.v3.webhooks import MessageEvent, PostbackEvent, TextMessageContent, AudioMessageContent
from core.container import container
from core.exceptions import AuthenticationError, AudioProcessingError
from core.logging_config import get_logger
from services.message_service import MessageService


logger = get_logger(__name__)


class MessageHandler:
    """Handler for LINE message events."""
    
    def __init__(self):
        """Initialize the message handler with required services."""
        self.auth_service = container.get('auth_service')
        self.audio_service = container.get('audio_service')
        self.user_repository = container.get('user_repository')
        self.message_service = MessageService(container.get('line_bot_api'))
        self.rich_menu_manager = container.get('rich_menu_manager')
    
    async def handle_text_message(self, event: MessageEvent) -> None:
        """
        Handle text message events.
        
        Args:
            event: LINE message event
        """
        try:
            message = event.message.text.strip()
            user_id = event.source.user_id
            
            logger.info(f"Handling text message from user {user_id}: {message[:50]}...")
            
            # Handle rich menu
            await self._handle_rich_menu(user_id)
            
            # Check user login status
            if not await self.auth_service.check_user_login(user_id, message):
                # User needs to complete registration
                await self._send_registration_prompt(event, user_id)
                return
            
            # Handle commands
            if message.startswith('/'):
                await self._handle_command(event, user_id, message)
                return
            
            # Handle regular messages
            await self._handle_regular_message(event, user_id, message)
            
        except AuthenticationError as e:
            logger.error(f"Authentication error: {e}")
            await self.message_service.send_text_message(
                event.reply_token,
                "Authentication failed. Please try again."
            )
        except Exception as e:
            logger.error(f"Error handling text message: {e}")
            await self.message_service.send_text_message(
                event.reply_token,
                "An error occurred. Please try again later."
            )
    
    async def handle_audio_message(self, event: MessageEvent) -> None:
        """
        Handle audio message events.
        
        Args:
            event: LINE message event
        """
        try:
            user_id = event.source.user_id
            
            logger.info(f"Handling audio message from user {user_id}")
            
            # Check user login
            if not self.user_repository.has_data(user_id):
                await self.message_service.send_text_message(
                    event.reply_token,
                    "Please complete registration first."
                )
                return
            
            # Show loading animation
            await self.message_service.show_loading_animation(user_id, 10)
            
            # Get and transcribe audio
            audio_content = await self.audio_service.get_audio_content(event.message.id)
            transcript = await self.audio_service.transcribe_audio(audio_content)
            
            logger.info(f"Transcribed audio: {transcript[:50]}...")
            
            # Process the transcript
            await self._process_audio_transcript(event, user_id, transcript, audio_content)
            
        except AudioProcessingError as e:
            logger.error(f"Audio processing error: {e}")
            await self.message_service.send_text_message(
                event.reply_token,
                "Failed to process audio. Please try again."
            )
        except Exception as e:
            logger.error(f"Error handling audio message: {e}")
            await self.message_service.send_text_message(
                event.reply_token,
                "An error occurred while processing audio."
            )
    
    async def handle_postback(self, event: PostbackEvent) -> None:
        """
        Handle postback events.
        
        Args:
            event: LINE postback event
        """
        try:
            user_id = event.source.user_id
            data = event.postback.data
            
            logger.info(f"Handling postback from user {user_id}: {data}")
            
            # Parse postback data
            params = dict(param.split('=') for param in data.split('&') if '=' in param)
            action = params.get('action')
            
            if action == 'select_category':
                await self._handle_category_selection(event, user_id, params)
            elif action == 'answer_question':
                await self._handle_question_answer(event, user_id, params)
            elif action == 'show_results':
                await self._handle_show_results(event, user_id)
            else:
                logger.warning(f"Unknown postback action: {action}")
            
        except Exception as e:
            logger.error(f"Error handling postback: {e}")
            await self.message_service.send_text_message(
                event.reply_token,
                "An error occurred. Please try again."
            )
    
    async def _handle_rich_menu(self, user_id: str) -> None:
        """Handle rich menu setup for user."""
        try:
            # Implementation would go here
            pass
        except Exception as e:
            logger.error(f"Error handling rich menu: {e}")
    
    async def _send_registration_prompt(self, event: MessageEvent, user_id: str) -> None:
        """Send registration prompt to user."""
        info = self.auth_service.user_data_enter.get(user_id, [])
        step = len(info)
        
        prompts = [
            "Please select your class period (1-5):",
            "Please enter your name:",
            "Please enter your student ID:",
            "Please enter your English name:"
        ]
        
        if step < len(prompts):
            await self.message_service.send_text_message(
                event.reply_token,
                prompts[step]
            )
    
    async def _handle_command(self, event: MessageEvent, user_id: str, command: str) -> None:
        """Handle user commands."""
        if command.startswith('/unlink') or command.startswith('/解除綁定'):
            await self.auth_service.unlink_user(user_id)
            await self.message_service.send_text_message(
                event.reply_token,
                "Successfully unlinked! / 已解除綁定！"
            )
        elif command.startswith('/魔法'):
            await self.auth_service.add_admin(user_id)
            await self.user_repository.save_config()
            await self.message_service.send_text_message(
                event.reply_token,
                "You are now an admin! / 你已變成管理員！"
            )
        else:
            await self.message_service.send_text_message(
                event.reply_token,
                "Unknown command. / 未知的指令。"
            )
    
    async def _handle_regular_message(self, event: MessageEvent, user_id: str, message: str) -> None:
        """Handle regular text messages."""
        # Implementation would include question handling, chat, etc.
        await self.message_service.send_text_message(
            event.reply_token,
            f"Received: {message}"
        )
    
    async def _process_audio_transcript(
        self,
        event: MessageEvent,
        user_id: str,
        transcript: str,
        audio_content: bytes
    ) -> None:
        """Process transcribed audio."""
        # Implementation would include assessment logic
        await self.message_service.send_text_message(
            event.reply_token,
            f"Transcription: {transcript}"
        )
    
    async def _handle_category_selection(
        self,
        event: PostbackEvent,
        user_id: str,
        params: dict
    ) -> None:
        """Handle category selection postback."""
        category = params.get('category')
        await self.message_service.send_text_message(
            event.reply_token,
            f"Selected category: {category}"
        )
    
    async def _handle_question_answer(
        self,
        event: PostbackEvent,
        user_id: str,
        params: dict
    ) -> None:
        """Handle question answer postback."""
        question_id = params.get('question_id')
        answer = params.get('answer')
        await self.message_service.send_text_message(
            event.reply_token,
            f"Answer received for question {question_id}"
        )
    
    async def _handle_show_results(self, event: PostbackEvent, user_id: str) -> None:
        """Handle show results postback."""
        # Get user's results
        user = self.user_repository.get_user(user_id)
        if user and user.history:
            result_text = "Your Results:\n"
            # Format results
            await self.message_service.send_text_message(
                event.reply_token,
                result_text
            )
        else:
            await self.message_service.send_text_message(
                event.reply_token,
                "No results available yet."
            )