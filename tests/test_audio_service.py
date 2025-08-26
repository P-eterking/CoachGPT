"""Unit tests for AudioService."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from io import BytesIO

from services.audio_service import AudioService


class TestAudioService:
    """Test cases for AudioService."""
    
    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client."""
        client = Mock()
        client.audio = Mock()
        client.audio.transcriptions = Mock()
        return client
    
    @pytest.fixture
    def mock_line_bot_api_blob(self):
        """Create a mock LINE Bot API blob client."""
        return Mock()
    
    @pytest.fixture
    def audio_service(self, mock_openai_client, mock_line_bot_api_blob):
        """Create an AudioService instance with mocked dependencies."""
        return AudioService(mock_openai_client, mock_line_bot_api_blob)
    
    @pytest.mark.asyncio
    async def test_get_audio_content_immediate(self, audio_service):
        """Test getting audio content when transcoding is complete."""
        # Arrange
        message_id = "test_message_id"
        expected_content = b"audio_content"
        
        result_mock = Mock()
        result_mock.status = 'completed'
        
        audio_service.line_bot_api_blob.get_message_content_transcoding_by_message_id = AsyncMock(
            return_value=result_mock
        )
        audio_service.line_bot_api_blob.get_message_content = AsyncMock(
            return_value=expected_content
        )
        
        # Act
        content = await audio_service.get_audio_content(message_id)
        
        # Assert
        assert content == expected_content
        audio_service.line_bot_api_blob.get_message_content_transcoding_by_message_id.assert_called_once_with(message_id)
        audio_service.line_bot_api_blob.get_message_content.assert_called_once_with(message_id)
    
    @pytest.mark.asyncio
    async def test_get_audio_content_with_processing(self, audio_service):
        """Test getting audio content when transcoding needs processing."""
        # Arrange
        message_id = "test_message_id"
        expected_content = b"audio_content"
        
        processing_result = Mock()
        processing_result.status = 'processing'
        
        completed_result = Mock()
        completed_result.status = 'completed'
        
        audio_service.line_bot_api_blob.get_message_content_transcoding_by_message_id = AsyncMock(
            side_effect=[processing_result, completed_result]
        )
        audio_service.line_bot_api_blob.get_message_content = AsyncMock(
            return_value=expected_content
        )
        
        # Act
        with patch('asyncio.sleep', new_callable=AsyncMock):
            content = await audio_service.get_audio_content(message_id)
        
        # Assert
        assert content == expected_content
        assert audio_service.line_bot_api_blob.get_message_content_transcoding_by_message_id.call_count == 2
    
    def test_convert_m4a_to_mp3_base64(self, audio_service):
        """Test M4A to MP3 conversion with base64 encoding."""
        # This test requires pydub and would need actual audio data
        # For unit testing, we'd typically mock the AudioSegment
        with patch('services.audio_service.AudioSegment') as mock_audio_segment:
            # Arrange
            mock_audio = Mock()
            mock_audio.export = Mock()
            mock_audio_segment.from_file.return_value = mock_audio
            
            test_content = b"fake_m4a_content"
            
            # Act
            result = audio_service.convert_m4a_to_mp3_base64(test_content)
            
            # Assert
            assert isinstance(result, str)
            mock_audio_segment.from_file.assert_called_once()
            mock_audio.export.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_transcribe_audio(self, audio_service):
        """Test audio transcription."""
        # Arrange
        test_content = b"audio_content"
        expected_transcript = "Hello, this is a test"
        
        transcript_obj = Mock()
        transcript_obj.text = f"  {expected_transcript}  "
        
        audio_service.client.audio.transcriptions.create = AsyncMock(
            return_value=transcript_obj
        )
        
        # Act
        with patch('tempfile.NamedTemporaryFile'):
            result = await audio_service.transcribe_audio(test_content)
        
        # Assert
        assert result == expected_transcript
        audio_service.client.audio.transcriptions.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_transcribe_audio_with_language(self, audio_service):
        """Test audio transcription with specific language."""
        # Arrange
        test_content = b"audio_content"
        expected_transcript = "你好，這是測試"
        language = "zh"
        
        transcript_obj = Mock()
        transcript_obj.text = expected_transcript
        
        audio_service.client.audio.transcriptions.create = AsyncMock(
            return_value=transcript_obj
        )
        
        # Act
        with patch('tempfile.NamedTemporaryFile'):
            result = await audio_service.transcribe_audio(test_content, language)
        
        # Assert
        assert result == expected_transcript
        # Verify language parameter was passed
        call_args = audio_service.client.audio.transcriptions.create.call_args
        assert call_args[1]['language'] == language