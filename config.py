import os
from linebot.v3.messaging import Configuration, AsyncApiClient, AsyncMessagingApi, AsyncMessagingApiBlob
from linebot.v3.webhook import WebhookParser
from openai import OpenAI
from groq import AsyncGroq

# 環境變數設定
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
DOMAIN = os.getenv("NGROK_DOMAIN")

# LINE Bot 配置
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(LINE_CHANNEL_SECRET)
async_api_client = AsyncApiClient(configuration)
line_bot_api = AsyncMessagingApi(async_api_client)
line_bot_api_blob = AsyncMessagingApiBlob(async_api_client)

# OpenAI 和 Groq 配置
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
groq = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

# 檔案儲存路徑
USER_STATE_FILE = 'user_state.json'
USER_DATA_FILE = 'user_data.json'