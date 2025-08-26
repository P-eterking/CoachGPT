"""
Centralized error handling utilities for consistent error management.
"""
import logging
from typing import Optional, Any
from functools import wraps

from utils.message_utils import send_text_message
from constants import ERROR_MESSAGES

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base application error class."""
    
    def __init__(self, message: str, error_code: str = 'generic_error', original_error: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.original_error = original_error


class ValidationError(AppError):
    """Error for validation failures."""
    
    def __init__(self, message: str, field: str = None, original_error: Optional[Exception] = None):
        super().__init__(message, 'validation_error', original_error)
        self.field = field


class ServiceError(AppError):
    """Error for service layer failures."""
    
    def __init__(self, message: str, service: str = None, original_error: Optional[Exception] = None):
        super().__init__(message, 'service_error', original_error)
        self.service = service


class ExternalApiError(AppError):
    """Error for external API failures."""
    
    def __init__(self, message: str, api: str = None, status_code: Optional[int] = None, original_error: Optional[Exception] = None):
        super().__init__(message, 'external_api_error', original_error)
        self.api = api
        self.status_code = status_code


def handle_errors(error_message_key: str = 'processing_error'):
    """
    Decorator for handling errors in handler methods.
    
    Args:
        error_message_key: Key for error message in ERROR_MESSAGES
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except AppError as e:
                logger.error(f"Application error in {func.__name__}: {e.message}", exc_info=e.original_error)
                # Send appropriate error message to user
                if len(args) > 1 and hasattr(args[1], 'source'):  # Check if second arg is event
                    event = args[1]
                    await send_text_message(event, ERROR_MESSAGES.get(error_message_key, ERROR_MESSAGES['processing_error']))
                return False
            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
                # Send generic error message to user
                if len(args) > 1 and hasattr(args[1], 'source'):  # Check if second arg is event
                    event = args[1]
                    await send_text_message(event, ERROR_MESSAGES.get(error_message_key, ERROR_MESSAGES['processing_error']))
                return False
        return wrapper
    return decorator


async def log_and_send_error(event: Any, error: Exception, error_key: str = 'processing_error') -> None:
    """
    Log error and send appropriate message to user.
    
    Args:
        event: The event to respond to
        error: The exception that occurred
        error_key: Key for error message in ERROR_MESSAGES
    """
    logger.error(f"Error processing event: {str(error)}", exc_info=True)
    await send_text_message(event, ERROR_MESSAGES.get(error_key, ERROR_MESSAGES['processing_error']))


def validate_required_fields(data: dict, required_fields: list[str]) -> None:
    """
    Validate that all required fields are present in data.
    
    Args:
        data: Dictionary to validate
        required_fields: List of required field names
        
    Raises:
        ValidationError: If any required field is missing
    """
    missing_fields = [field for field in required_fields if field not in data or data[field] is None]
    if missing_fields:
        raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")


def safe_int_conversion(value: str, field_name: str = "value") -> int:
    """
    Safely convert string to integer.
    
    Args:
        value: String value to convert
        field_name: Name of the field for error messages
        
    Returns:
        Converted integer value
        
    Raises:
        ValidationError: If conversion fails
    """
    try:
        return int(value)
    except (ValueError, TypeError) as e:
        raise ValidationError(f"Invalid {field_name}: must be a valid integer", field_name, e)