import os
from linebot.v3.messaging import Configuration, AsyncApiClient, AsyncMessagingApi, AsyncMessagingApiBlob
from linebot.v3.webhook import WebhookParser
from openai import AsyncOpenAI
from groq import AsyncGroq
from manager import QuestionManager
from manager.richmenu import RichMenuManager
# 環境變數設定
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
DOMAIN = os.getenv("DOMAIN")

# LINE Bot 配置
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(LINE_CHANNEL_SECRET)
async_api_client = AsyncApiClient(configuration)
line_bot_api = AsyncMessagingApi(async_api_client)
line_bot_api_blob = AsyncMessagingApiBlob(async_api_client)
rich_menu_manager = RichMenuManager(line_bot_api, line_bot_api_blob)

# OpenAI 和 Groq 配置
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
groq = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

# 問題管理器
question_manager = QuestionManager(data_source='./category')

# 檔案儲存路徑
# USER_STATE_FILE = 'user_state.json'
USER_DATA_FILE = 'user_data.json'
CONFIG_FILE = 'config.json'