import os
from typing import Optional
from linebot.v3.messaging import Configuration, AsyncApiClient, AsyncMessagingApi, AsyncMessagingApiBlob
from linebot.v3.webhook import WebhookParser
from openai import AsyncOpenAI
# from groq import AsyncGroq
from manager import QuestionManager
from manager.richmenu import RichMenuManager
from constants import USER_DATA_FILE, CONFIG_FILE


class AppConfig:
    """Application configuration class."""
    
    def __init__(self):
        # Environment variables
        self.line_channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        self.line_channel_secret = os.getenv("LINE_CHANNEL_SECRET")
        self.domain = os.getenv("DOMAIN")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # Validate required environment variables
        self._validate_env_vars()
        
        # Initialize LINE Bot components
        self.configuration = Configuration(access_token=self.line_channel_access_token)
        self.parser = WebhookParser(self.line_channel_secret)
        self.async_api_client = AsyncApiClient(self.configuration)
        self.line_bot_api = AsyncMessagingApi(self.async_api_client)
        self.line_bot_api_blob = AsyncMessagingApiBlob(self.async_api_client)
        self.rich_menu_manager = RichMenuManager(self.line_bot_api, self.line_bot_api_blob)
        
        # Initialize OpenAI client
        self.openai_client = AsyncOpenAI(api_key=self.openai_api_key)
        
        # Initialize question manager
        self.question_manager = QuestionManager(data_source='./category')
    
    def _validate_env_vars(self) -> None:
        """Validate that all required environment variables are set."""
        required_vars = {
            'LINE_CHANNEL_ACCESS_TOKEN': self.line_channel_access_token,
            'LINE_CHANNEL_SECRET': self.line_channel_secret,
            'DOMAIN': self.domain,
            'OPENAI_API_KEY': self.openai_api_key,
        }
        
        missing_vars = [name for name, value in required_vars.items() if not value]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")


# Global configuration instance
app_config = AppConfig()

# Backward compatibility - expose individual components
LINE_CHANNEL_ACCESS_TOKEN = app_config.line_channel_access_token
LINE_CHANNEL_SECRET = app_config.line_channel_secret
DOMAIN = app_config.domain
configuration = app_config.configuration
parser = app_config.parser
async_api_client = app_config.async_api_client
line_bot_api = app_config.line_bot_api
line_bot_api_blob = app_config.line_bot_api_blob
rich_menu_manager = app_config.rich_menu_manager
client = app_config.openai_client
question_manager = app_config.question_manager