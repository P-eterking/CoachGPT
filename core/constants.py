"""Application constants and configuration values."""

from typing import List, Tuple

# Chat categories and related constants
CHAT_CATEGORIES: List[str] = [
    "旅遊 Travel", 
    "運動 Sports", 
    "面試 Interview", 
    "英語技巧 English Skills"
]

CHAT_CATEGORY_IMAGE_URLS: List[str] = [
    "/templates/chat/travel.jpg", 
    "/templates/chat/sports.jpg", 
    "/templates/chat/interview.jpg", 
    "/templates/chat/english_skills.jpg"
]

# Image file extensions
IMAGE_EXTENSIONS: Tuple[str, ...] = (
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'
)

# Model configurations
TRANSCRIPTION_MODEL: str = "gpt-4o-mini-transcribe"
FALLBACK_TRANSCRIPTION_MODEL: str = "whisper-1"

# Registration flow constants
REGISTRATION_STEPS: List[str] = [
    "class_period",
    "name", 
    "student_id",
    "english_name"
]

CLASS_PERIOD_OPTIONS: Tuple[int, int] = (1, 5)  # Min and max values

# File paths
DEFAULT_USER_DATA_FILE: str = 'user_data.json'
DEFAULT_CONFIG_FILE: str = 'config.json'

# Default configuration structure
DEFAULT_CONFIG: dict = {
    'admins': [],
    'rich_menu': {},
    'settings': {}
}

# Category name mappings for analysis
CATEGORY_NAME_MAP: dict = {
    'ex1': (0, 0),
    'ex2': (0, 1),
    'ex3': (0, 2),
    'pretest': (1, 0),
    'posttest': (2, 0)
}

# Timezone for timestamps
DEFAULT_TIMEZONE: str = 'Asia/Taipei'

# Auto-save interval in seconds
AUTO_SAVE_INTERVAL: int = 60

# Maximum retries for API calls
MAX_API_RETRIES: int = 3

# Timeout values in seconds
API_TIMEOUT: int = 30
TRANSCRIPTION_TIMEOUT: int = 60