"""Message service for handling LINE message operations."""

from typing import Optional, List, Dict, Any
from linebot.v3.messaging import (
    ReplyMessageRequest, TextMessage, FlexMessage,
    QuickReply, QuickReplyItem, PostbackAction,
    ShowLoadingAnimationRequest
)
from core.logging_config import get_logger


class MessageService:
    """Service for handling LINE message operations."""
    
    def __init__(self, line_bot_api):
        """
        Initialize the message service.
        
        Args:
            line_bot_api: LINE Bot API client
        """
        self.line_bot_api = line_bot_api
        self.logger = get_logger(__name__)
    
    async def send_text_message(self, reply_token: str, text: str) -> None:
        """
        Send a text message.
        
        Args:
            reply_token: Reply token from the event
            text: Text message to send
        """
        try:
            await self.line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=text)]
                )
            )
            self.logger.debug(f"Sent text message: {text[:50]}...")
        except Exception as e:
            self.logger.error(f"Failed to send text message: {e}")
            raise
    
    async def send_flex_message(
        self,
        reply_token: str,
        alt_text: str,
        contents: Dict[str, Any]
    ) -> None:
        """
        Send a flex message.
        
        Args:
            reply_token: Reply token from the event
            alt_text: Alternative text for notifications
            contents: Flex message contents
        """
        try:
            await self.line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[FlexMessage(alt_text=alt_text, contents=contents)]
                )
            )
            self.logger.debug(f"Sent flex message: {alt_text}")
        except Exception as e:
            self.logger.error(f"Failed to send flex message: {e}")
            raise
    
    async def send_quick_reply(
        self,
        reply_token: str,
        text: str,
        quick_reply_items: List[Dict[str, str]]
    ) -> None:
        """
        Send a message with quick reply buttons.
        
        Args:
            reply_token: Reply token from the event
            text: Text message
            quick_reply_items: List of quick reply items with 'label' and 'data'
        """
        try:
            items = [
                QuickReplyItem(
                    action=PostbackAction(
                        label=item['label'],
                        data=item['data']
                    )
                )
                for item in quick_reply_items
            ]
            
            await self.line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[
                        TextMessage(
                            text=text,
                            quick_reply=QuickReply(items=items)
                        )
                    ]
                )
            )
            self.logger.debug(f"Sent quick reply message with {len(items)} options")
        except Exception as e:
            self.logger.error(f"Failed to send quick reply: {e}")
            raise
    
    async def show_loading_animation(self, chat_id: str, duration: int = 5) -> None:
        """
        Show loading animation in the chat.
        
        Args:
            chat_id: Chat ID (user or group)
            duration: Duration in seconds (max 60)
        """
        try:
            await self.line_bot_api.show_loading_animation(
                ShowLoadingAnimationRequest(
                    chatId=chat_id,
                    loadingSeconds=min(duration, 60)
                )
            )
            self.logger.debug(f"Showing loading animation for {duration}s")
        except Exception as e:
            self.logger.error(f"Failed to show loading animation: {e}")
            # Don't raise as this is not critical
    
    async def reply_message(self, reply_token: str, messages: List[Any]) -> None:
        """
        Send multiple messages as a reply.
        
        Args:
            reply_token: Reply token from the event
            messages: List of message objects
        """
        try:
            await self.line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=messages
                )
            )
            self.logger.debug(f"Sent {len(messages)} messages")
        except Exception as e:
            self.logger.error(f"Failed to reply messages: {e}")
            raise