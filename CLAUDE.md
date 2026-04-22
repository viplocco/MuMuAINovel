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

**快速启动：**
```bash
cp backend/.env.example .env
# 编辑 .env 填入 API Key 等配置
docker-compose up -d
docker-compose logs -f
```

**Docker 构建流程（多阶段构建）：**
1. **阶段1 (frontend-builder)**：Node 22 构建 React 前端
   - 输出静态文件到 `dist` 目录
2. **阶段2 (python:3.11-slim)**：运行后端服务
   - 安装 PyTorch CPU 版本 + Python 依赖
   - 复制 embedding 模型（约 400MB）
   - 复制前端构建产物到 `/app/static`
   - 使用 `entrypoint.sh` 启动

**服务架构（docker-compose.yml）：**
- `postgres`：PostgreSQL 18 数据库
  - 端口: 5432，数据持久化: `postgres_data` volume
  - 初始化脚本: `backend/scripts/init_postgres.sql`
  - 优化配置支持 80-150 并发用户
- `mumuainovel`：主应用服务
  - 端口: 8000，日志目录: `./logs`
  - 配置挂载: `.env` 文件，Chroma 数据: `chroma_data` volume
  - 自动等待数据库就绪后启动

**容器启动流程（entrypoint.sh）：**
1. 等待 PostgreSQL 就绪（最多 30 秒）
2. 执行 `alembic upgrade head` 数据库迁移
3. 启动 uvicorn 服务

**PostgreSQL 初始化（init_postgres.sql）：**
- 安装 `uuid-ossp` 扩展（UUID 生成）
- 安装 `pg_trgm` 扩展（模糊搜索）

**常用命令：**
```bash
docker-compose up -d          # 启动服务
docker-compose ps             # 查看状态
docker-compose logs -f        # 查看日志
docker-compose restart        # 重启服务
docker-compose down           # 停止服务
docker-compose pull           # 更新镜像
docker stats                  # 资源使用
```

**Docker Hub 镜像：**
```bash
docker pull mumujie/mumuainovel:latest
# 镜像已包含 embedding 模型，无需额外下载
```

**环境变量传递：**
- `.env` 文件挂载到 `/app/.env:ro`
- 关键变量通过 docker-compose.yml 环境段传递
- 数据库密码通过 `POSTGRES_PASSWORD` 配置

### 数据库迁移

```bash
alembic upgrade head                           # 应用迁移
alembic revision --autogenerate -m "描述"      # 创建新迁移
```

**迁移目录结构：**
- PostgreSQL 迁移：`backend/alembic/postgres/versions/`
- SQLite 迁移（已弃用）：`backend/alembic/sqlite/versions/`

## 架构

### 后端结构

```
backend/app/
├── api/           # REST API 路由（27+ 路由文件）
├── models/        # SQLAlchemy ORM 模型（35+ 个模型）
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
├── pages/         # 页面组件（28+ 个页面）
├── components/    # 可复用 UI 组件
├── services/      # Axios API 客户端
├── store/         # Zustand 状态管理
├── types/         # TypeScript 类型定义
├── utils/         # 工具函数（sseClient 等）
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
- 前端使用 `SSEPostClient` 处理 POST 请求的流式响应
- 消息类型：`progress`、`chunk`、`result`、`error`、`done`

**会话管理：**
- 基于 Cookie 的会话，可配置过期时间（默认 120 分钟）
- 多种认证方式：本地账号、LinuxDO OAuth、邮箱验证码

**MCP (Model Context Protocol) 集成：**
- `MCPClientFacade` 提供统一的 MCP 操作入口（单例模式）
- 支持插件注册、工具调用、批量执行
- 自动将 MCP 工具转换为 OpenAI Function Calling 格式
- 工具命名格式：`plugin_tool` 或 `plugin.tool`
- 支持连接类型：`streamable_http`、`sse`
- 用户可在前端 `/mcp-plugins` 页面管理 MCP 插件

**伏笔追踪系统：**
- `Foreshadow` 模型支持伏笔的埋入、回收、废弃状态管理
- 状态流转：planted → resolved / abandoned
- 情节分析 `PLOT_ANALYSIS` 提示词自动识别伏笔并关联已有伏笔 ID
- 支持 `reference_foreshadow_id` 字段追踪回收的伏笔

**物品管理系统：**
- 支持物品的出现、流转、消耗、状态变更追踪
- `Item` 模型包含稀有度、品质、属性、别名等字段
- `ItemCategory` 支持分类树结构
- `ItemTransfer` 记录物品持有权变更历史
- 章节分析可自动识别物品变化并同步

**职业等级体系：**
- `Career` 和 `CareerTemplate` 支持自定义职业和等级系统
- 角色可拥有主职业和副职业，每个职业有多个阶段
- `CharacterCareer` 关联角色与职业

**拆书导入功能：**
- `bookImportApi` 支持从 TXT 文件导入已有小说
- 流程：创建任务 → 解析章节 → 生成预览 → 应用导入（流式）
- 自动反向生成项目信息和章节大纲

**节奏分析功能：**
- `/api/outlines/rhythm-analysis/{project_id}` 提供章节类型分布和节奏强度曲线数据
- 支持 17 种细粒度章节类型：主线推进、支线展开、过渡、小高潮、大高潮、人物关系、感情线、奇遇事件、秘境副本、反派视角、日常互动、战斗、修炼成长、势力冲突、伏笔埋设、伏笔回收
- 数据维度区分：`data_level` 标识数据来源（chapter 或 outline）
- 前端通过横向柱状图可视化展示节奏强度

**伏笔预警功能：**
- 伏笔状态自动追踪：planted（已埋入）、resolved（已回收）、abandoned（已废弃）
- 上下文优先级管理：AI 生成时智能引用相关伏笔
- 预警机制：检测未回收伏笔并提醒作者

**章节摘要管理：**
- 章节生成后自动创建摘要记录
- 支持手动编辑和 AI 辅助生成
- 用于构建 AI 上下文，提升连续性

### 数据库模型（核心）

| 模型 | 说明 |
|------|------|
| `Project` | 小说项目，包含世界观设定 |
| `Outline` | 章节大纲，层级结构 |
| `Chapter` | 生成的章节内容 |
| `Character` | 角色档案及属性 |
| `CharacterRelationship` | 角色间关系 |
| `Organization` | 故事中的组织/势力 |
| `OrganizationMember` | 组织成员关系 |
| `Career` | 自定义职业/等级体系 |
| `CareerTemplate` | 职业模板库 |
| `CharacterCareer` | 角色职业关联 |
| `StoryMemory` | AI 上下文的长期记忆 |
| `PlotAnalysis` | 情节分析记录 |
| `Foreshadow` | 伏笔追踪 |
| `Item` | 物品管理 |
| `ItemCategory` | 物品分类 |
| `ItemTransfer` | 物品流转记录 |
| `ItemAttributeChange` | 物品属性变更 |
| `ItemQuantityChange` | 物品数量变更 |
| `ItemStatusChange` | 物品状态变更 |
| `WritingStyle` | 自定义写作风格 |
| `PromptTemplate` | 用户自定义提示词模板 |
| `PromptWorkshopItem` | 提示词工坊内容 |
| `PromptSubmission` | 提示词提交记录 |
| `PromptWorkshopLike` | 提示词点赞记录 |
| `MCPPlugin` | MCP 工具配置 |
| `User` | 用户账户 |
| `UserPassword` | 用户密码记录 |
| `Settings` | 用户个人设置 |
| `SystemDecorationConfig` | 系统装饰配置（全局装饰管理） |
| `AnalysisTask` | 分析任务记录 |
| `BatchGenerationTask` | 批量生成任务 |
| `RegenerationTask` | 重生成任务 |
| `GenerationHistory` | 生成历史记录 |
| `ProjectDefaultStyle` | 项目默认风格设置 |
| `RelationshipType` | 关系类型定义 |

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

### DeepSeek 模型特殊处理

`AIService.generate_text()` 中对 DeepSeek 模型有特殊处理：
- 自动限制 `max_tokens` 为 4096（DeepSeek 上限）
- 禁用 MCP 工具（DeepSeek 不支持 Function Calling）

### 前端 Ant Design 5.x 规范

避免使用已废弃的 API：
- `dropdownRender` → 使用 `popupRender`
- `bodyStyle` → 使用 `styles.body`
- `bordered` → 使用 `variant`
- `InputNumber` 的 `addonAfter` → 使用 `Space.Compact`
- `Spin` 的 `tip` 属性需要嵌套子元素才能显示
- 静态方法 `message.error()` 等无法使用动态主题，推荐在组件内使用 `App.useApp()` 获取 message 实例

### 前端 SSE 流式通信

使用 `ssePost()` 函数处理流式 POST 请求：
```typescript
import { ssePost } from '../utils/sseClient';

const result = await ssePost('/api/wizard-stream/world-building', data, {
  onProgress: (msg, progress, status) => console.log(msg),
  onChunk: (content) => console.log(content),
  onError: (error) => console.error(error),
});
```

### MCP 工具调用

`AIService` 自动加载用户启用的 MCP 工具：
- 创建服务时传入 `user_id` 和 `db_session`
- `generate_text()` 和 `generate_text_stream()` 自动检查 MCP 配置
- 可通过 `auto_mcp=False` 临时禁用 MCP
- 通过 `mcp_max_rounds` 控制工具调用轮数（默认 3）

### 提示词工坊模式

- `WORKSHOP_MODE=client`：本地部署实例，从云端获取提示词
- `WORKSHOP_MODE=server`：云端中央服务器（仅 mumuverse.space）

## 常见问题

### Embedding 模型文件

从源码构建需要下载 embedding 模型文件（约 400MB），放置到：
```
backend/embedding/models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2/
```

使用 Docker Hub 镜像时，模型文件已包含在镜像中。

### 连接池配置

高并发场景下的 PostgreSQL 连接池参数：
- `DATABASE_POOL_SIZE=50`（核心连接）
- `DATABASE_MAX_OVERFLOW=30`（溢出连接）
- `DATABASE_POOL_TIMEOUT=90`（超时秒数）
- `DATABASE_POOL_RECYCLE=1800`（回收时间）