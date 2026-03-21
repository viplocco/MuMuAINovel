# 多阶段构建 Dockerfile for AI Story Creator
# 支持多架构构建: linux/amd64, linux/arm64

# 设置 Docker 镜像源
# 使用国内镜像加速构建

# 阶段1: 构建前端
FROM docker.1ms.run/library/node:22-bookworm AS frontend-builder

ARG USE_CN_MIRROR

# 安装构建原生模块所需的系统依赖
RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /frontend

# 复制所有前端文件（node_modules 会被 .dockerignore 排除）
COPY frontend/ ./

# 清理可能残留的 Windows node_modules
RUN rm -rf node_modules package-lock.json

# 根据参数决定是否使用国内npm镜像
RUN if [ "$USE_CN_MIRROR" = "true" ]; then \
        npm config set registry https://registry.npmmirror.com; \
    fi

# 清理 package-lock.json 以避免因镜像源不一致导致的 404 错误
RUN rm -f package-lock.json

# 安装依赖（在 Linux 环境下安装正确的平台包）
RUN npm install

# 临时修改vite配置，使其输出到dist目录（而不是../backend/static）
RUN sed -i "s|outDir: '../backend/static'|outDir: 'dist'|g" vite.config.ts

# 构建前端
RUN npm run build

# 阶段2: 构建最终镜像
FROM docker.1ms.run/library/python:3.11-slim

ARG USE_CN_MIRROR
ARG TARGETPLATFORM
ARG TARGETARCH

# 设置工作目录
WORKDIR /app

# 根据参数决定是否使用国内镜像源
RUN if [ "$USE_CN_MIRROR" = "true" ]; then \
        sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources && \
        sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources; \
    fi

# 安装系统依赖（添加数据库工具）
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# 复制后端依赖文件
COPY backend/requirements.txt ./

# 根据架构安装PyTorch CPU版本
# arm64架构使用pip直接安装，amd64使用PyTorch官方CPU源
RUN if [ "$TARGETARCH" = "arm64" ]; then \
        pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu || \
        pip install --no-cache-dir torch; \
    else \
        pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu; \
    fi

# 安装其他Python依赖
RUN if [ "$USE_CN_MIRROR" = "true" ]; then \
        pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/; \
    else \
        pip install --no-cache-dir -r requirements.txt; \
    fi

# 创建embedding目录
RUN mkdir -p /app/embedding

# 复制本地已有的 embedding 模型（从构建主机）
COPY backend/embedding /app/embedding

# 设置 Sentence-Transformers 缓存目录
ENV SENTENCE_TRANSFORMERS_HOME=/app/embedding

# 复制后端代码（不包含embedding，因为已经下载了）
COPY backend/ ./

# 从前端构建阶段复制构建好的静态文件
COPY --from=frontend-builder /frontend/dist ./static

# 复制 Alembic 迁移配置和脚本（PostgreSQL）
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