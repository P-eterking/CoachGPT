"""
Constants module for centralizing configuration values and magic strings.
"""

# File paths
USER_DATA_FILE = 'user_data.json'
CONFIG_FILE = 'config.json'

# Audio processing
AUDIO_TRANSCRIPTION_MODEL = "gpt-4o-mini-transcribe"
AUDIO_LANGUAGE_DEFAULT = "en"
AUDIO_PROCESSING_SLEEP_INTERVAL = 1  # seconds
AUDIO_LOADING_TIMEOUT = 30  # seconds

# Assessment
ASSESSMENT_MODEL = "gpt-4o"
ASSESSMENT_MAX_COMPLETION_TOKENS = 2048
ASSESSMENT_TEMPERATURE = 1
ASSESSMENT_MIN_SCORE = 0
ASSESSMENT_MAX_SCORE = 10

# Chat categories
CHAT_CATEGORIES = ["旅遊 Travel", "運動 Sports", "面試 Interview", "英語技巧 English Skills"]
CHAT_CATEGORY_IMAGES = [
    "/templates/chat/travel.jpg",
    "/templates/chat/sports.jpg", 
    "/templates/chat/interview.jpg",
    "/templates/chat/english_skills.jpg"
]

# User validation
MAX_STUDENT_ID_LENGTH = 8
MIN_TEXT_LENGTH = 1

# Category mappings
CATEGORY_NAME_MAP = {
    'ex1': (0, 0),
    'ex2': (0, 1),
    'ex3': (0, 2),
    'pretest': (1, 0),
    'posttest': (2, 0)
}

KNOWN_CATEGORIES = ['ex1', 'ex2', 'ex3', 'pretest', 'posttest']
CHAT_ENABLED_CATEGORIES = ['chat', 'sex', 'accent', 'audio']

# File extensions
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')

# Error messages
ERROR_MESSAGES = {
    'audio_content_failed': "無法獲取音訊內容，請稍後再試。\nUnable to get audio content, please try again later.",
    'transcription_failed': "文字轉錄發生錯誤，請稍後再試。\nAn error occurred, please try again later.",
    'processing_error': "處理時發生錯誤，請稍後再試。\nAn error occurred during processing, please try again later.",
    'student_id_format_error': "學號格式錯誤！\nFormat error!",
    'unit_unavailable': "該單元目前不可用。\nCurrently unavailable.",
    'select_unit': "請選擇單元。\nPlease select a unit.",
    'login_required': "請先綁定學號。\nPlease bind your student ID first."
}

# Success messages
SUCCESS_MESSAGES = {
    'binding_complete': "綁定完成 你好! {name}\nSuccess! Hello, {name} !",
}

# Default configuration
DEFAULT_CONFIG = {
    'admin': [],
    'rich_menu_ids': {},
    'enabled': [],
    'response': []
}