"""
Service interfaces for defining contracts and improving testability.
"""
from abc import ABC, abstractmethod
from typing import Optional, List

from utils.models import User, UserState, SpeechAssessment, Question


class IAudioService(ABC):
    """Interface for audio processing services."""
    
    @abstractmethod
    async def get_audio_content(self, message_id: str) -> Optional[bytes]:
        """Get audio content from message ID."""
        pass
    
    @abstractmethod
    def convert_m4a_to_mp3_base64(self, message_content: bytes) -> str:
        """Convert M4A audio to MP3 base64."""
        pass
    
    @abstractmethod
    async def transcribe_audio(self, message_content: bytes, language: str = "en") -> Optional[str]:
        """Transcribe audio content to text."""
        pass


class IAssessmentService(ABC):
    """Interface for assessment services."""
    
    @abstractmethod
    async def assess_speech(self, question: Question, user_answer: str) -> Optional[SpeechAssessment]:
        """Assess user's speech response."""
        pass
    
    @abstractmethod
    def validate_assessment(self, assessment: SpeechAssessment) -> bool:
        """Validate assessment results."""
        pass


class IUserService(ABC):
    """Interface for user management services."""
    
    @abstractmethod
    def get_user_state(self, user_id: str) -> UserState:
        """Get or create user state."""
        pass
    
    @abstractmethod
    def get_user_data(self, user_id: str) -> Optional[User]:
        """Get user data by ID."""
        pass
    
    @abstractmethod
    def is_user_logged_in(self, user_id: str) -> bool:
        """Check if user is logged in."""
        pass
    
    @abstractmethod
    def validate_student_id(self, student_id: str) -> tuple[bool, Optional[str]]:
        """Validate student ID format."""
        pass
    
    @abstractmethod
    def create_user(self, user_id: str, class_time: int, department: str, student_id: str, name: str) -> User:
        """Create a new user."""
        pass
    
    @abstractmethod
    def delete_user(self, user_id: str) -> bool:
        """Delete user data."""
        pass
    
    @abstractmethod
    def add_assessment_to_history(self, user_id: str, category: str, assessment: SpeechAssessment) -> bool:
        """Add assessment to user's history."""
        pass
    
    @abstractmethod
    def get_user_history(self, user_id: str, category: str) -> List[SpeechAssessment]:
        """Get user's assessment history."""
        pass
    
    @abstractmethod
    def get_registration_success_message(self, name: str) -> str:
        """Get formatted registration success message."""
        pass


class IQuestionManager(ABC):
    """Interface for question management."""
    
    @abstractmethod
    def has_question(self, category: str) -> bool:
        """Check if category has questions."""
        pass
    
    @abstractmethod
    def get_question(self, category: str, sub: int) -> Optional[Question]:
        """Get question by category and sub-index."""
        pass
    
    @abstractmethod
    async def load_questions(self) -> None:
        """Load questions from data source."""
        pass