"""Audio processing service for handling audio transcription and conversion."""

import asyncio
import base64
import tempfile
from io import BytesIO
from typing import Optional

from pydub import AudioSegment
from openai import AsyncOpenAI


class AudioService:
    """Service for handling audio-related operations."""
    
    def __init__(self, openai_client: AsyncOpenAI, line_bot_api_blob):
        """
        Initialize the audio service.
        
        Args:
            openai_client: OpenAI client for transcription
            line_bot_api_blob: LINE Bot API blob client for fetching audio content
        """
        self.client = openai_client
        self.line_bot_api_blob = line_bot_api_blob
    
    async def get_audio_content(self, message_id: str) -> bytes:
        """
        Fetch audio content from LINE messaging API.
        
        Args:
            message_id: The message ID to fetch audio content for
            
        Returns:
            The audio content as bytes
        """
        result = await self.line_bot_api_blob.get_message_content_transcoding_by_message_id(message_id)
        
        # Wait for transcoding to complete
        while result.status == 'processing':
            await asyncio.sleep(1)
            result = await self.line_bot_api_blob.get_message_content_transcoding_by_message_id(message_id)
        
        return await self.line_bot_api_blob.get_message_content(message_id)
    
    @staticmethod
    def convert_m4a_to_mp3_base64(message_content: bytes) -> str:
        """
        Convert M4A audio to MP3 format and encode as base64.
        
        Args:
            message_content: The M4A audio content as bytes
            
        Returns:
            Base64 encoded MP3 audio string
        """
        m4a_file = BytesIO(message_content)
        audio = AudioSegment.from_file(m4a_file, format="m4a")
        
        mp3_io = BytesIO()
        audio.export(mp3_io, format="mp3")
        mp3_bytes = mp3_io.getvalue()
        
        return base64.b64encode(mp3_bytes).decode('utf-8')
    
    async def transcribe_audio(self, message_content: bytes, language: str = "en") -> str:
        """
        Transcribe audio content using OpenAI's transcription service.
        
        Args:
            message_content: The audio content to transcribe
            language: The language code for transcription (default: "en")
            
        Returns:
            The transcribed text
        """
        with tempfile.NamedTemporaryFile(suffix=".m4a", delete=True) as f:
            f.write(message_content)
            f.seek(0)
            f.flush()
            
            transcript_obj = await self.client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",  # or "whisper-1"
                file=(f.name, f.read()),
                language=language,
            )
            
            return transcript_obj.text.strip()