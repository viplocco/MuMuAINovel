# 多阶段构建 Dockerfile for AI Story Creator
# 支持多架构构建: linux/amd64, linux/arm64
# 默认使用国内镜像加速构建

# 阶段1: 构建前端
FROM docker.1ms.run/library/node:22-bookworm AS frontend-builder

# 设置工作目录
WORKDIR /frontend

# 复制所有前端文件（node_modules 会被 .dockerignore 排除）
COPY frontend/ ./

# 清理可能残留的 Windows node_modules
RUN rm -rf node_modules package-lock.json

# 使用国内 npm 镜像
RUN npm config set registry https://registry.npmmirror.com

# 安装依赖（在 Linux 环境下安装正确的平台包）
RUN npm install

# 临时修改 vite 配置，使其输出到 dist 目录
RUN sed -i "s|outDir: '../backend/static'|outDir: 'dist'|g" vite.config.ts

# 构建前端
RUN npm run build

# 阶段2: 构建最终镜像
FROM docker.1ms.run/library/python:3.11-slim

# 设置工作目录
WORKDIR /app

# 使用国内 apt 镜像源
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# 复制后端依赖文件
COPY backend/requirements.txt ./

# 使用国内 pip 镜像安装 PyTorch CPU 版本
RUN pip config set global.timeout 600 && \
    pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ torch --index-url https://download.pytorch.org/whl/cpu || \
    pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ torch

# 安装其他 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 创建 embedding 目录
RUN mkdir -p /app/embedding

# 复制本地已有的 embedding 模型
COPY backend/embedding /app/embedding

# 设置 Sentence-Transformers 缓存目录
ENV SENTENCE_TRANSFORMERS_HOME=/app/embedding

# 复制后端代码
COPY backend/ ./

# 从前端构建阶段复制构建好的静态文件
COPY --from=frontend-builder /frontend/dist ./static

# 复制 Alembic 迁移配置和脚本
COPY backend/alembic-postgres.ini ./alembic.ini
COPY backend/alembic/postgres ./alembic
COPY backend/scripts/entrypoint.sh /app/entrypoint.sh
COPY backend/scripts/migrate.py ./scripts/migrate.py

# 转换脚本为 Unix 换行符并设置执行权限
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# 创建必要的目录
RUN mkdir -p /app/data /app/logs

# 暴露端口
EXPOSE 8000

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV APP_HOST=0.0.0.0
ENV APP_PORT=8000

# 设置运行时为离线模式（模型已在构建时下载）
ENV TRANSFORMERS_OFFLINE=1
ENV HF_DATASETS_OFFLINE=1
ENV HF_HUB_OFFLINE=1

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# 使用 entrypoint 脚本启动（自动执行迁移）
ENTRYPOINT ["/app/entrypoint.sh"]