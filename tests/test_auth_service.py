"""Unit tests for AuthService."""

import pytest
from unittest.mock import Mock, AsyncMock

from services.auth_service import AuthService


class TestAuthService:
    """Test cases for AuthService."""
    
    @pytest.fixture
    def mock_user_repository(self):
        """Create a mock user repository."""
        repo = Mock()
        repo.has_data = Mock(return_value=False)
        repo.create_user = AsyncMock()
        repo.delete_user = AsyncMock()
        repo.add_admin = AsyncMock()
        return repo
    
    @pytest.fixture
    def auth_service(self, mock_user_repository):
        """Create an AuthService instance with mocked dependencies."""
        return AuthService(mock_user_repository)
    
    @pytest.mark.asyncio
    async def test_check_user_login_existing_user(self, auth_service):
        """Test login check for existing user."""
        # Arrange
        user_id = "test_user"
        auth_service.user_repository.has_data.return_value = True
        
        # Act
        result = await auth_service.check_user_login(user_id, "message")
        
        # Assert
        assert result is True
        auth_service.user_repository.has_data.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_check_user_login_new_user_no_message(self, auth_service):
        """Test login check for new user without message."""
        # Arrange
        user_id = "test_user"
        auth_service.user_repository.has_data.return_value = False
        
        # Act
        result = await auth_service.check_user_login(user_id, None)
        
        # Assert
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_user_login_back_command(self, auth_service):
        """Test handling 'back' command during registration."""
        # Arrange
        user_id = "test_user"
        auth_service.user_repository.has_data.return_value = False
        auth_service.user_data_enter[user_id] = ["1", "John Doe"]
        
        # Act
        result = await auth_service.check_user_login(user_id, "back")
        
        # Assert
        assert result is False
        assert auth_service.user_data_enter[user_id] == ["1"]
    
    def test_validate_registration_input_class_period_valid(self, auth_service):
        """Test validation of valid class period input."""
        # Arrange
        info = []
        message = "3"
        
        # Act
        result = auth_service._validate_registration_input(info, message)
        
        # Assert
        assert result['valid'] is True
    
    def test_validate_registration_input_class_period_invalid(self, auth_service):
        """Test validation of invalid class period input."""
        # Arrange
        info = []
        message = "6"  # Out of range
        
        # Act
        result = auth_service._validate_registration_input(info, message)
        
        # Assert
        assert result['valid'] is False
        assert result['error'] == 'out_of_range'
    
    def test_validate_registration_input_class_period_non_digit(self, auth_service):
        """Test validation of non-digit class period input."""
        # Arrange
        info = []
        message = "abc"
        
        # Act
        result = auth_service._validate_registration_input(info, message)
        
        # Assert
        assert result['valid'] is False
        assert result['error'] == 'format_error'
    
    def test_validate_registration_input_name(self, auth_service):
        """Test validation of name input."""
        # Arrange
        info = ["1"]  # Class period already entered
        
        # Act - Valid name
        result = auth_service._validate_registration_input(info, "John Doe")
        assert result['valid'] is True
        
        # Act - Empty name
        result = auth_service._validate_registration_input(info, "  ")
        assert result['valid'] is False
        assert result['error'] == 'empty_name'
    
    def test_validate_registration_input_student_id(self, auth_service):
        """Test validation of student ID input."""
        # Arrange
        info = ["1", "John Doe"]
        
        # Act - Valid student ID
        result = auth_service._validate_registration_input(info, "12345")
        assert result['valid'] is True
        
        # Act - Empty student ID
        result = auth_service._validate_registration_input(info, "")
        assert result['valid'] is False
        assert result['error'] == 'empty_student_id'
    
    def test_validate_registration_input_english_name(self, auth_service):
        """Test validation of English name input."""
        # Arrange
        info = ["1", "John Doe", "12345"]
        
        # Act - Valid English name
        result = auth_service._validate_registration_input(info, "John")
        assert result['valid'] is True
        
        # Act - Empty English name
        result = auth_service._validate_registration_input(info, "   ")
        assert result['valid'] is False
        assert result['error'] == 'empty_english_name'
    
    @pytest.mark.asyncio
    async def test_complete_registration(self, auth_service):
        """Test completing user registration."""
        # Arrange
        user_id = "test_user"
        info = ["2", "John Doe", "12345", "John"]
        
        # Act
        await auth_service._complete_registration(user_id, info)
        
        # Assert
        auth_service.user_repository.create_user.assert_called_once_with(
            user_id,
            {
                'class_period': '2',
                'name': 'John Doe',
                'student_id': '12345',
                'english_name': 'John'
            }
        )
    
    @pytest.mark.asyncio
    async def test_unlink_user(self, auth_service):
        """Test unlinking a user."""
        # Arrange
        user_id = "test_user"
        auth_service.user_data_enter[user_id] = ["partial", "data"]
        
        # Act
        await auth_service.unlink_user(user_id)
        
        # Assert
        auth_service.user_repository.delete_user.assert_called_once_with(user_id)
        assert user_id not in auth_service.user_data_enter
    
    @pytest.mark.asyncio
    async def test_add_admin(self, auth_service):
        """Test adding admin privileges to a user."""
        # Arrange
        user_id = "test_user"
        
        # Act
        await auth_service.add_admin(user_id)
        
        # Assert
        auth_service.user_repository.add_admin.assert_called_once_with(user_id)
    
    def test_get_required_fields_count(self, auth_service):
        """Test getting the required fields count."""
        # Act
        count = auth_service._get_required_fields_count()
        
        # Assert
        assert count == 4  # Class period, Name, Student ID, English name