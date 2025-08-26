"""
Audio processing service for handling audio transcription and conversion.
"""
import asyncio
import base64
import tempfile
from io import BytesIO
from typing import Optional

from pydub import AudioSegment
from openai import AsyncOpenAI

from interfaces.services import IAudioService
from constants import AUDIO_TRANSCRIPTION_MODEL, AUDIO_PROCESSING_SLEEP_INTERVAL


class AudioService(IAudioService):
    """Service for handling audio processing operations."""
    
    def __init__(self, openai_client: AsyncOpenAI, line_bot_api_blob) -> None:
        self.client = openai_client
        self.line_bot_api_blob = line_bot_api_blob
    
    async def get_audio_content(self, message_id: str) -> Optional[bytes]:
        """
        Get audio content from LINE Bot API with transcoding support.
        
        Args:
            message_id: The message ID from LINE Bot
            
        Returns:
            Audio content as bytes or None if failed
        """
        try:
            result = await self.line_bot_api_blob.get_message_content_transcoding_by_message_id(message_id)
            
            # Wait for transcoding to complete
            while result.status == 'processing':
                await asyncio.sleep(AUDIO_PROCESSING_SLEEP_INTERVAL)
                result = await self.line_bot_api_blob.get_message_content_transcoding_by_message_id(message_id)
            
            return await self.line_bot_api_blob.get_message_content(message_id)
        except Exception as e:
            print(f"Error getting audio content: {e}")
            return None
    
    def convert_m4a_to_mp3_base64(self, message_content: bytes) -> str:
        """
        Convert M4A audio content to MP3 format encoded as base64.
        
        Args:
            message_content: M4A audio content as bytes
            
        Returns:
            Base64 encoded MP3 audio
        """
        m4a_file = BytesIO(message_content)
        audio = AudioSegment.from_file(m4a_file, format="m4a")
        mp3_io = BytesIO()
        audio.export(mp3_io, format="mp3")
        mp3_bytes = mp3_io.getvalue()
        return base64.b64encode(mp3_bytes).decode('utf-8')
    
    async def transcribe_audio(self, message_content: bytes, language: str = "en") -> Optional[str]:
        """
        Transcribe audio content using OpenAI Whisper.
        
        Args:
            message_content: Audio content as bytes
            language: Language code for transcription
            
        Returns:
            Transcribed text or None if failed
        """
        try:
            with tempfile.NamedTemporaryFile(suffix=".m4a", delete=True) as f:
                f.write(message_content)
                f.seek(0)
                f.flush()
                
                transcript_obj = await self.client.audio.transcriptions.create(
                    model=AUDIO_TRANSCRIPTION_MODEL,
                    file=(f.name, f.read()),
                    language=language,
                )
                
                return transcript_obj.text.strip()
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None