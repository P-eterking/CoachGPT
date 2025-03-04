#!/bin/bash
# # 設置 Ngrok 

# # 設置 ngrok authtoken
# ngrok config add-authtoken $NGROK_AUTHTOKEN

# if [ -n "$NGROK_DOMAIN" ]; then
#     # 啟動 ngrok 並公開 8000 端口
#     ngrok http --domain=$NGROK_DOMAIN 8000 &
# else
#     ngrok http 8000 &
# fi

# 啟動 FastAPI 應用程式
uvicorn app:app --reload --host 0.0.0.0 --port $PORT