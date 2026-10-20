# 智能装配说明书生成系统 - 后端Dockerfile
# 基于 Python 3.11 + Debian 12 Bookworm（Bullseye 已结束 LTS）

FROM python:3.11-slim-bookworm

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# 安装系统依赖
# PDF处理依赖:
# - ghostscript: PDF渲染引擎
# - poppler-utils: PDF工具集 (pdfinfo, pdftotext等)
# - default-jre: Java运行环境 (tabula-py需要)
# OpenCV依赖:
# - libgl1: OpenGL库
# - libglib2.0-0: GLib库
# - libsm6, libxext6, libxrender-dev: X11库
# Camelot依赖:
# - libgomp1: OpenMP库
# 字体支持:
# - fonts-wqy-zenhei: 文泉驿正黑中文字体
# - fonts-wqy-microhei: 文泉驿微米黑中文字体
RUN apt-get update && apt-get install -y --no-install-recommends \
    ghostscript \
    poppler-utils \
    default-jre \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    fonts-wqy-zenhei \
    fonts-wqy-microhei \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖（使用 pip 默认官方源）
RUN pip install --no-cache-dir -r requirements.txt

# 复制核心源码（白名单）
COPY backend ./backend
COPY core ./core
COPY agents ./agents
COPY processors ./processors
COPY utils ./utils
COPY models ./models
COPY prompts ./prompts
COPY config.py ./config.py
COPY api.py ./api.py

# 创建必要的目录
RUN mkdir -p uploads output static pipeline_output temp logs debug_output

# 暴露端口
EXPOSE 8008

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8008/api/health')" || exit 1

# 启动命令
CMD ["uvicorn", "backend.simple_app:app", "--host", "0.0.0.0", "--port", "8008"]

