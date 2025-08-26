"""
Dependency injection container for managing service dependencies.
"""
from typing import Optional

from services.audio_service import AudioService
from services.assessment_service import AssessmentService
from services.user_service import UserService


class ServiceContainer:
    """Container for managing service dependencies."""
    
    def __init__(self):
        self._audio_service: Optional[AudioService] = None
        self._assessment_service: Optional[AssessmentService] = None
        self._user_service: Optional[UserService] = None
    
    def set_audio_service(self, service: AudioService) -> None:
        """Set the audio service instance."""
        self._audio_service = service
    
    def get_audio_service(self) -> AudioService:
        """Get the audio service instance."""
        if self._audio_service is None:
            raise RuntimeError("AudioService not initialized")
        return self._audio_service
    
    def set_assessment_service(self, service: AssessmentService) -> None:
        """Set the assessment service instance."""
        self._assessment_service = service
    
    def get_assessment_service(self) -> AssessmentService:
        """Get the assessment service instance."""
        if self._assessment_service is None:
            raise RuntimeError("AssessmentService not initialized")
        return self._assessment_service
    
    def set_user_service(self, service: UserService) -> None:
        """Set the user service instance."""
        self._user_service = service
    
    def get_user_service(self) -> UserService:
        """Get the user service instance."""
        if self._user_service is None:
            raise RuntimeError("UserService not initialized")
        return self._user_service


# Global container instance
container = ServiceContainer()