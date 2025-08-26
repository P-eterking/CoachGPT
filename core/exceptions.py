"""Custom exceptions for the application."""


class BaseAppException(Exception):
    """Base exception for the application."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AuthenticationError(BaseAppException):
    """Exception raised for authentication errors."""
    pass


class ValidationError(BaseAppException):
    """Exception raised for validation errors."""
    pass


class DataNotFoundError(BaseAppException):
    """Exception raised when requested data is not found."""
    pass


class ExternalAPIError(BaseAppException):
    """Exception raised for external API errors."""
    pass


class ConfigurationError(BaseAppException):
    """Exception raised for configuration errors."""
    pass


class AudioProcessingError(BaseAppException):
    """Exception raised for audio processing errors."""
    pass


class QuestionNotFoundError(BaseAppException):
    """Exception raised when a question is not found."""
    pass


class UserNotFoundError(DataNotFoundError):
    """Exception raised when a user is not found."""
    pass


class PermissionDeniedError(BaseAppException):
    """Exception raised when user lacks required permissions."""
    pass