"""Authentication service for handling user login and validation."""

from typing import Dict, List, Optional


class AuthService:
    """Service for handling user authentication and validation."""
    
    def __init__(self, user_repository):
        """
        Initialize the authentication service.
        
        Args:
            user_repository: Repository for user data operations
        """
        self.user_repository = user_repository
        self.user_data_enter: Dict[str, List[str]] = {}
    
    async def check_user_login(self, user_id: str, message: Optional[str] = None) -> bool:
        """
        Check if a user is logged in or needs to complete registration.
        
        Args:
            user_id: The user ID to check
            message: Optional message from the user
            
        Returns:
            True if the user is logged in, False otherwise
        """
        # Check if user already has data
        if self.user_repository.has_data(user_id):
            return True
        
        # Handle registration flow
        info = self.user_data_enter.get(user_id, [])
        
        if message is None:
            return False
        
        # Handle navigation commands
        if message.lower() == 'back' and len(info) > 0:
            self.user_data_enter[user_id] = info[:-1]
            return False
        
        # Validate input based on registration step
        validation_result = self._validate_registration_input(info, message)
        if not validation_result['valid']:
            return False
        
        # Add valid input to registration data
        info.append(message)
        self.user_data_enter[user_id] = info
        
        # Check if registration is complete
        if len(info) >= self._get_required_fields_count():
            # Complete registration
            await self._complete_registration(user_id, info)
            del self.user_data_enter[user_id]
            return True
        
        return False
    
    def _validate_registration_input(self, info: List[str], message: str) -> Dict[str, bool]:
        """
        Validate user input based on registration step.
        
        Args:
            info: Current registration information
            message: User's input message
            
        Returns:
            Dictionary with validation result
        """
        step = len(info)
        
        # Step 0: Class period selection (1-5)
        if step == 0:
            if not message.isdigit():
                return {'valid': False, 'error': 'format_error'}
            
            option = int(message)
            if option < 1 or option > 5:
                return {'valid': False, 'error': 'out_of_range'}
            
            return {'valid': True}
        
        # Step 1: Name input
        elif step == 1:
            if not message.strip():
                return {'valid': False, 'error': 'empty_name'}
            return {'valid': True}
        
        # Step 2: Student ID
        elif step == 2:
            if not message.strip():
                return {'valid': False, 'error': 'empty_student_id'}
            return {'valid': True}
        
        # Step 3: English name
        elif step == 3:
            if not message.strip():
                return {'valid': False, 'error': 'empty_english_name'}
            return {'valid': True}
        
        return {'valid': False, 'error': 'unknown_step'}
    
    def _get_required_fields_count(self) -> int:
        """Get the number of required fields for registration."""
        return 4  # Class period, Name, Student ID, English name
    
    async def _complete_registration(self, user_id: str, info: List[str]):
        """
        Complete user registration with provided information.
        
        Args:
            user_id: The user ID
            info: List of registration information
        """
        user_data = {
            'class_period': info[0],
            'name': info[1],
            'student_id': info[2],
            'english_name': info[3]
        }
        
        await self.user_repository.create_user(user_id, user_data)
    
    async def unlink_user(self, user_id: str):
        """
        Unlink/remove a user's data.
        
        Args:
            user_id: The user ID to unlink
        """
        await self.user_repository.delete_user(user_id)
        
        # Clean up any pending registration data
        if user_id in self.user_data_enter:
            del self.user_data_enter[user_id]
    
    async def add_admin(self, user_id: str):
        """
        Grant admin privileges to a user.
        
        Args:
            user_id: The user ID to make admin
        """
        await self.user_repository.add_admin(user_id)