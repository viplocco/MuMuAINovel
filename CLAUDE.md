# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码仓库中工作时提供指导。
始终用简体中文与用户交流，除非用户要求用其他语言。

## 项目概述

MuMuAINovel 是一个 AI 驱动的智能小说创作助手。用户可以在 AI 辅助下创作小说，包括生成大纲、角色、章节和世界观设定。

**技术栈：**
- 后端：FastAPI + PostgreSQL (SQLAlchemy async) + Alembic 数据库迁移
- 前端：React + TypeScript + Vite + Ant Design 5.x + Zustand
- AI：OpenAI SDK、Anthropic SDK、Gemini（通过 OpenAI 兼容 API）
- 向量检索：sentence-transformers + ChromaDB 语义搜索

## 开发命令

### 后端 (Python 3.11+)

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API 密钥和数据库配置

# 运行数据库迁移
alembic upgrade head

# 启动开发服务器
python -m uvicorn app.main:app --host localhost --port 8000 --reload
```

### 前端

```bash
cd frontend

npm install
npm run dev      # 开发服务器（代理到 localhost:8000）
npm run build    # 生产构建，输出到 ../backend/static
npm run lint     # ESLint 检查
```

### Docker 部署

```bash
cp backend/.env.example .env
# 编辑 .env
docker-compose up -d
docker-compose logs -f
```

### 数据库迁移

```bash
alembic upgrade head                           # 应用迁移
alembic revision --autogenerate -m "描述"      # 创建新迁移
```

## 架构

### 后端结构

```
backend/app/
├── api/           # REST API 路由（25+ 路由文件）
├── models/        # SQLAlchemy ORM 模型（21 个模型）
├── services/      # 业务逻辑层
├── middleware/    # 认证和请求 ID 中间件
├── mcp/           # Model Context Protocol 集成
├── schemas/       # Pydantic 请求/响应模式
├── database.py    # PostgreSQL 连接池
├── main.py        # FastAPI 应用入口
└── config.py      # 环境配置
```

### 前端结构

```
frontend/src/
├── pages/         # 页面组件（27 个页面）
├── components/    # 可复用 UI 组件
├── services/      # Axios API 客户端
├── store/         # Zustand 状态管理
├── types/         # TypeScript 类型定义
└── App.tsx        # React 路由配置
```

### 核心架构模式

**多租户数据隔离：**
- 所有模型包含 `user_id` 字段
- `get_db()` 依赖从 `request.state.user_id` 提取用户 ID
- PostgreSQL 共享数据库，行级隔离

**AI 服务抽象：**
- `AIService` 类为 OpenAI、Anthropic、Gemini 提供统一接口
- `ai_providers/` 使用提供者模式适配各 AI 厂商
- 启用时自动集成 MCP 工具
- 用户可通过 `PromptTemplate` 自定义提示词模板，系统会优先使用用户模板

**提示词模板系统：**
- `PromptService` 管理所有 AI 提示词
- 支持用户自定义模板覆盖系统默认模板
- 模板使用 Python f-string 格式，注意 `{{` 和 `}}` 表示字面花括号
- 模板键名格式：`SCENE_ACTION_SYSTEM`、`SCENE_ACTION_USER` 等

**流式响应：**
- 使用 SSE (Server-Sent Events) 流式传输 AI 生成内容
- 用于向导流、章节生成、大纲扩展

**会话管理：**
- 基于 Cookie 的会话，可配置过期时间（默认 120 分钟）
- 多种认证方式：本地账号和 LinuxDO OAuth

### 数据库模型（核心）

| 模型 | 说明 |
|------|------|
| `Project` | 小说项目，包含世界观设定 |
| `Outline` | 章节大纲，层级结构 |
| `Chapter` | 生成的章节内容 |
| `Character` | 角色档案及属性 |
| `CharacterRelationship` | 角色间关系 |
| `Organization` | 故事中的组织/势力 |
| `Career` | 自定义职业/等级体系 |
| `StoryMemory` | AI 上下文的长期记忆 |
| `Foreshadow` | 伏笔追踪 |
| `WritingStyle` | 自定义写作风格 |
| `PromptTemplate` | 用户自定义提示词模板 |
| `MCPPlugin` | MCP 工具配置 |

## 必需的环境变量

```bash
# 数据库
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/mumuai_novel

# AI 服务（至少需要一个）
OPENAI_API_KEY=your_key
OPENAI_BASE_URL=https://api.openai.com/v1
# 或
GEMINI_API_KEY=your_key
# 或
ANTHROPIC_API_KEY=your_key

# 认证
LOCAL_AUTH_ENABLED=true
LOCAL_AUTH_USERNAME=admin
LOCAL_AUTH_PASSWORD=admin123
```

## API 文档

本地运行时：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 数据库驱动说明

本项目使用 `psycopg[binary]` (psycopg3) 进行同步数据库操作（迁移），而非 `psycopg2-binary`。异步操作使用 `asyncpg`。支持 PostgreSQL 18。

## 重要配置说明

### AI Provider 配置

`DEFAULT_AI_PROVIDER` 只支持三种值：`openai`、`anthropic`、`gemini`。

使用 OpenAI 兼容 API（如 DeepSeek、通义千问等）时：
- `DEFAULT_AI_PROVIDER=openai`（不是 deepseek）
- `OPENAI_BASE_URL=https://api.deepseek.com`（或其他兼容端点）
- `DEFAULT_MODEL=deepseek-chat`（模型名称）

### 前端 Ant Design 5.x 规范

避免使用已废弃的 API：
- `dropdownRender` → 使用 `popupRender`
- `bodyStyle` → 使用 `styles.body`
- `bordered` → 使用 `variant`
- `InputNumber` 的 `addonAfter` → 使用 `Space.Compact`
- `Spin` 的 `tip` 属性需要嵌套子元素才能显示
- 静态方法 `message.error()` 等无法使用动态主题，推荐在组件内使用 `App.useApp()` 获取 message 实例