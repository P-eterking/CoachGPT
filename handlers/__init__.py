"""
Handlers package for organizing event handlers.
"""
from handlers.text_handler import TextHandler
from handlers.audio_handler import AudioHandler
from handlers.postback_handler import PostbackHandler

# Create handler instances
text_handler = TextHandler()
audio_handler = AudioHandler()
postback_handler = PostbackHandler()

# Export handler functions for backward compatibility
async def handle_text_message(event):
    """Handle text message events."""
    return await text_handler.handle(event)

async def handle_audio_message(event):
    """Handle audio message events."""
    return await audio_handler.handle(event)

async def handle_postback(event):
    """Handle postback events."""
    return await postback_handler.handle(event)