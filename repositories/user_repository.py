"""Repository for user data operations."""

import json
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path
from utils.models import User


class UserRepository:
    """Repository for managing user data persistence."""
    
    def __init__(self, data_file: str = 'user_data.json', config_file: str = 'config.json'):
        """
        Initialize the user repository.
        
        Args:
            data_file: Path to the user data JSON file
            config_file: Path to the configuration JSON file
        """
        self.data_file = Path(data_file)
        self.config_file = Path(config_file)
        self.user_data: Dict[str, User] = {}
        self.config: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
    
    async def load_user_data(self):
        """Load user data from the JSON file."""
        async with self._lock:
            if self.data_file.exists():
                try:
                    with open(self.data_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.user_data = {
                            user_id: User(**user_data) 
                            for user_id, user_data in data.items()
                        }
                except Exception as e:
                    print(f"Error loading user data: {e}")
                    self.user_data = {}
            else:
                self.user_data = {}
    
    async def save_user_data(self):
        """Save user data to the JSON file."""
        async with self._lock:
            try:
                data = {
                    user_id: user.model_dump() 
                    for user_id, user in self.user_data.items()
                }
                with open(self.data_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"Error saving user data: {e}")
    
    async def load_config(self):
        """Load configuration from the JSON file."""
        async with self._lock:
            if self.config_file.exists():
                try:
                    with open(self.config_file, 'r', encoding='utf-8') as f:
                        self.config = json.load(f)
                except Exception as e:
                    print(f"Error loading config: {e}")
                    self.config = {
                        'admins': [],
                        'rich_menu': {},
                        'settings': {}
                    }
            else:
                self.config = {
                    'admins': [],
                    'rich_menu': {},
                    'settings': {}
                }
    
    async def save_config(self):
        """Save configuration to the JSON file."""
        async with self._lock:
            try:
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"Error saving config: {e}")
    
    def has_data(self, user_id: str) -> bool:
        """
        Check if user data exists.
        
        Args:
            user_id: The user ID to check
            
        Returns:
            True if user data exists, False otherwise
        """
        return user_id in self.user_data
    
    def get_user(self, user_id: str) -> Optional[User]:
        """
        Get user data by ID.
        
        Args:
            user_id: The user ID
            
        Returns:
            User object if found, None otherwise
        """
        return self.user_data.get(user_id)
    
    def get_all_users(self) -> Dict[str, User]:
        """
        Get all user data.
        
        Returns:
            Dictionary of all users
        """
        return self.user_data.copy()
    
    async def create_user(self, user_id: str, user_data: Dict[str, Any]):
        """
        Create a new user.
        
        Args:
            user_id: The user ID
            user_data: Dictionary containing user information
        """
        async with self._lock:
            # Create a new User object with default values
            self.user_data[user_id] = User(
                id=user_data.get('student_id', ''),
                name=user_data.get('name', ''),
                english_name=user_data.get('english_name', ''),
                class_period=user_data.get('class_period', ''),
                history={},
                chat_history={},
                state={}
            )
    
    async def update_user(self, user_id: str, updates: Dict[str, Any]):
        """
        Update user data.
        
        Args:
            user_id: The user ID
            updates: Dictionary of fields to update
        """
        async with self._lock:
            if user_id in self.user_data:
                user = self.user_data[user_id]
                for key, value in updates.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
    
    async def delete_user(self, user_id: str):
        """
        Delete a user.
        
        Args:
            user_id: The user ID to delete
        """
        async with self._lock:
            if user_id in self.user_data:
                del self.user_data[user_id]
    
    def get_user_state(self, user_id: str, key: str, default: Any = None) -> Any:
        """
        Get a specific state value for a user.
        
        Args:
            user_id: The user ID
            key: The state key
            default: Default value if key not found
            
        Returns:
            The state value or default
        """
        user = self.get_user(user_id)
        if user:
            return user.state.get(key, default)
        return default
    
    async def set_user_state(self, user_id: str, key: str, value: Any):
        """
        Set a specific state value for a user.
        
        Args:
            user_id: The user ID
            key: The state key
            value: The value to set
        """
        async with self._lock:
            if user_id in self.user_data:
                self.user_data[user_id].state[key] = value
    
    def get_user_history(self, user_id: str) -> Dict[str, List[Any]]:
        """
        Get user's assessment history.
        
        Args:
            user_id: The user ID
            
        Returns:
            Dictionary of assessment history
        """
        user = self.get_user(user_id)
        return user.history if user else {}
    
    async def add_history_entry(self, user_id: str, question_key: str, assessment: Any):
        """
        Add an assessment entry to user's history.
        
        Args:
            user_id: The user ID
            question_key: The question identifier
            assessment: The assessment data
        """
        async with self._lock:
            if user_id in self.user_data:
                if question_key not in self.user_data[user_id].history:
                    self.user_data[user_id].history[question_key] = []
                self.user_data[user_id].history[question_key].append(assessment)
    
    def is_admin(self, user_id: str) -> bool:
        """
        Check if a user is an admin.
        
        Args:
            user_id: The user ID to check
            
        Returns:
            True if user is admin, False otherwise
        """
        return user_id in self.config.get('admins', [])
    
    async def add_admin(self, user_id: str):
        """
        Add a user as admin.
        
        Args:
            user_id: The user ID to make admin
        """
        async with self._lock:
            if 'admins' not in self.config:
                self.config['admins'] = []
            if user_id not in self.config['admins']:
                self.config['admins'].append(user_id)
    
    def get_rich_menu_config(self, key: str) -> Optional[str]:
        """
        Get rich menu configuration.
        
        Args:
            key: The configuration key
            
        Returns:
            Configuration value if found
        """
        return self.config.get('rich_menu', {}).get(key)
    
    async def set_rich_menu_config(self, key: str, value: str):
        """
        Set rich menu configuration.
        
        Args:
            key: The configuration key
            value: The configuration value
        """
        async with self._lock:
            if 'rich_menu' not in self.config:
                self.config['rich_menu'] = {}
            self.config['rich_menu'][key] = value