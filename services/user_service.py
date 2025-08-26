"""
User service for handling user registration, validation, and data management.
"""
from typing import Optional, List, Dict

from utils.models import User, UserState, SpeechAssessment
from interfaces.services import IUserService
from constants import MAX_STUDENT_ID_LENGTH, ERROR_MESSAGES, SUCCESS_MESSAGES


class UserService(IUserService):
    """Service for handling user operations."""
    
    def __init__(self, user_data: Dict[str, User], user_state: Dict[str, UserState]) -> None:
        self.user_data = user_data
        self.user_state = user_state
    
    def get_user_state(self, user_id: str) -> UserState:
        """
        Get or create user state.
        
        Args:
            user_id: The user ID
            
        Returns:
            UserState object
        """
        if self.user_state.get(user_id) is None:
            self.user_state[user_id] = UserState()
        return self.user_state.get(user_id)
    
    def get_user_data(self, user_id: str) -> Optional[User]:
        """
        Get user data by ID.
        
        Args:
            user_id: The user ID
            
        Returns:
            User object or None if not found
        """
        return self.user_data.get(user_id)
    
    def is_user_logged_in(self, user_id: str) -> bool:
        """
        Check if user is logged in (has registered).
        
        Args:
            user_id: The user ID
            
        Returns:
            True if user is logged in, False otherwise
        """
        return user_id in self.user_data
    
    def validate_student_id(self, student_id: str) -> tuple[bool, Optional[str]]:
        """
        Validate student ID format.
        
        Args:
            student_id: The student ID to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not student_id.isdigit():
            return False, ERROR_MESSAGES['student_id_format_error']
        
        if len(student_id) > MAX_STUDENT_ID_LENGTH:
            return False, ERROR_MESSAGES['student_id_format_error']
        
        return True, None
    
    def create_user(
        self, 
        user_id: str, 
        class_time: int, 
        department: str, 
        student_id: str, 
        name: str
    ) -> User:
        """
        Create a new user with the provided information.
        
        Args:
            user_id: LINE user ID
            class_time: Class time slot
            department: User's department
            student_id: Student ID number
            name: User's name
            
        Returns:
            Created User object
        """
        user = User(
            dep=department,
            id=student_id,
            name=name,
            class_time=class_time,
            history={},
            chat={}
        )
        self.user_data[user_id] = user
        return user
    
    def delete_user(self, user_id: str) -> bool:
        """
        Delete user data.
        
        Args:
            user_id: The user ID to delete
            
        Returns:
            True if user was deleted, False if user didn't exist
        """
        if user_id in self.user_data:
            del self.user_data[user_id]
            return True
        return False
    
    def add_assessment_to_history(
        self, 
        user_id: str, 
        category: str, 
        assessment: SpeechAssessment
    ) -> bool:
        """
        Add assessment result to user's history.
        
        Args:
            user_id: The user ID
            category: The question category
            assessment: The assessment result
            
        Returns:
            True if added successfully, False otherwise
        """
        user = self.get_user_data(user_id)
        if not user:
            return False
        
        if category not in user.history:
            user.history[category] = []
        
        user.history[category].append(assessment)
        return True
    
    def get_user_history(self, user_id: str, category: str) -> List[SpeechAssessment]:
        """
        Get user's assessment history for a specific category.
        
        Args:
            user_id: The user ID
            category: The question category
            
        Returns:
            List of SpeechAssessment objects
        """
        user = self.get_user_data(user_id)
        if not user or category not in user.history:
            return []
        
        return user.history[category]
    
    def get_registration_success_message(self, name: str) -> str:
        """
        Get formatted registration success message.
        
        Args:
            name: User's name
            
        Returns:
            Formatted success message
        """
        return SUCCESS_MESSAGES['binding_complete'].format(name=name)