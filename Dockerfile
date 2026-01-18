# 基礎映像
FROM python:3.12-alpine
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 設置環境變數，防止 Python 生成 .pyc 文件
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1

# 安裝所需的依賴項，包括 curl 和 bash（Alpine 默認使用 /bin/sh，但我們明確需要 bash）
RUN apk update && apk add --no-cache \
    bash \
    curl \
    # gcc \
    libc-dev \
    linux-headers \
    libffi-dev \
    openssl-dev \
    ffmpeg 

# 下載並安裝 ngrok
# RUN curl -Lo /usr/local/bin/ngrok https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz && \
#     tar -xvzf /usr/local/bin/ngrok -C /usr/local/bin && \
#     chmod +x /usr/local/bin/ngrok

# 複製應用代碼
COPY . /app/

# 設置工作目錄
WORKDIR /app

RUN uv pip install --no-cache-dir -r requirements.txt

RUN echo "vm.swappiness=10" >> /etc/sysctl.conf

# 確保 start.sh 是 Unix 格式並設置執行權限
RUN chmod +x /app/start.sh

# 開放端口
EXPOSE 8000

# 使用 bash 執行啟動腳本來啟動 FastAPI 和 Ngrok
# CMD ["uvicorn", "app:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
CMD ["bash", "./start.sh"]