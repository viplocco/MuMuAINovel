# MuMuAINovel 部署文档

> 本文档记录项目的详细部署步骤、配置说明及日常维护命令。
>
> 生成时间：2026-03-08 19:02  
> 适用版本：v1.3.6

---

## 📋 目录

1. [环境要求](#-环境要求)
2. [项目结构](#-项目结构)
3. [部署步骤](#-部署步骤)
4. [配置说明](#-配置说明)
5. [启动与停止](#-启动与停止)
6. [日常维护](#-日常维护)
7. [故障排查](#-故障排查)

---

## 🖥️ 环境要求

### 最低配置

| 组件 | 要求 |
|------|------|
| **操作系统** | Windows 10/11, Linux, macOS |
| **Python** | 3.11+ (推荐 3.11-3.12) |
| **Node.js** | 18+ |
| **内存** | 4 GB RAM |
| **存储** | 10 GB 可用空间 |
| **网络** | 稳定互联网连接（调用 AI API） |

### 推荐配置

| 组件 | 要求 |
|------|------|
| **CPU** | 4 核 |
| **内存** | 8 GB RAM |
| **存储** | 20 GB SSD |
| **数据库** | PostgreSQL 15+ 或 Neon 云数据库 |

---

## 📁 项目结构

```
MuMuAINovel/
├── backend/                 # 后端服务
│   ├── app/                # 应用代码
│   │   ├── api/           # API 路由
│   │   ├── models/        # 数据模型
│   │   ├── services/      # 业务逻辑
│   │   └── main.py        # 应用入口
│   ├── .venv/             # Python 虚拟环境
│   ├── embedding/         # Embedding 模型文件
│   ├── logs/              # 日志目录
│   ├── static/            # 前端构建产物
│   ├── scripts/           # 工具脚本
│   ├── .env               # 环境配置文件
│   └── requirements.txt   # Python 依赖
├── frontend/               # 前端应用
│   ├── src/               # 源代码
│   ├── node_modules/      # 依赖包
│   ├── package.json       # 项目配置
│   └── dist/              # 构建产物
├── DEPLOYMENT.md          # 本文档
└── README.md              # 项目说明
```

---

## 🚀 部署步骤

### 步骤 1: 克隆项目

```bash
# 进入项目目录
cd E:\project\lean\MuMuAINovel\MuMuAINovel
```

### 步骤 2: 后端环境配置

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

**⚠️ 注意**: Python 3.13 需要升级依赖包：
```bash
pip install --upgrade sqlalchemy fastapi pydantic uvicorn
```

### 步骤 3: 配置环境变量

创建 `.env` 文件（位于 `backend/.env`）：

```env
# 应用配置
APP_NAME=MuMuAINovel
APP_VERSION=1.3.6
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=false
TZ=Asia/Shanghai

# 数据库配置（PostgreSQL）
DATABASE_URL=postgresql+asyncpg://neondb_owner:npg_QBEd2wHC0FsM@ep-mute-mud-a495xzkk-pooler.us-east-1.aws.neon.tech:5432/neondb

# 或使用本地 PostgreSQL:
# DATABASE_URL=postgresql+asyncpg://mumuai:123456@localhost:5432/mumuai_novel

# 或使用 SQLite:
# DATABASE_URL=sqlite+aiosqlite:///./mumuai_novel.db

# 日志配置
LOG_LEVEL=INFO
LOG_TO_FILE=true
LOG_FILE_PATH=logs/app.log
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=30

# AI 服务配置
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.deepseek.com
DEFAULT_AI_PROVIDER=deepseek
DEFAULT_MODEL=deepseek-chat
DEFAULT_TEMPERATURE=0.7
DEFAULT_MAX_TOKENS=8192

# OAuth 配置（可选）
LINUXDO_CLIENT_ID=11111
LINUXDO_CLIENT_SECRET=11111
LINUXDO_REDIRECT_URI=http://localhost:8000/api/auth/callback
FRONTEND_URL=http://localhost:8000

# 本地账户登录
LOCAL_AUTH_ENABLED=true
LOCAL_AUTH_USERNAME=admin
LOCAL_AUTH_PASSWORD=your_password_here
LOCAL_AUTH_DISPLAY_NAME=本地管理员

# 会话配置
SESSION_EXPIRE_MINUTES=120
SESSION_REFRESH_THRESHOLD_MINUTES=30
```

### 步骤 4: 前端构建

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 安装缺失的依赖（如有报错）
npm install dagre @xyflow/react --save

# 构建前端
npm run build
```

构建成功后，产物会自动复制到 `backend/static/` 目录。

### 步骤 5: 启动服务

```bash
# 进入后端目录
cd backend

# 设置环境变量
set PYTHONPATH=E:\project\lean\MuMuAINovel\MuMuAINovel\backend

# 启动服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## ⚙️ 配置说明

### 数据库配置选项

#### 选项 1: Neon 云数据库（推荐）

```env
DATABASE_URL=postgresql+asyncpg://用户名:密码@主机:5432/数据库名
```

**优点**：
- 无需本地安装 PostgreSQL
- 自动备份
- 全球 CDN 加速

#### 选项 2: 本地 PostgreSQL

```env
DATABASE_URL=postgresql+asyncpg://mumuai:123456@localhost:5432/mumuai_novel
```

**安装 PostgreSQL**：
```powershell
# 下载地址: https://www.postgresql.org/download/windows/
# 安装后创建数据库:
# CREATE DATABASE mumuai_novel;
# CREATE USER mumuai WITH PASSWORD '123456';
# GRANT ALL PRIVILEGES ON DATABASE mumuai_novel TO mumuai;
```

#### 选项 3: SQLite（测试用）

```env
DATABASE_URL=sqlite+aiosqlite:///./mumuai_novel.db
```

**优点**：无需安装数据库，适合测试  
**缺点**：不适合高并发，功能有限

### AI 服务配置

支持多种 AI 提供商：

```env
# DeepSeek
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.deepseek.com
DEFAULT_MODEL=deepseek-chat

# OpenAI
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
DEFAULT_MODEL=gpt-4o-mini

# 其他中转 API
OPENAI_BASE_URL=https://your-proxy.com/v1
```

---

## 🎮 启动与停止

### 启动服务

#### 方式 1: 命令行启动（推荐开发环境）

```powershell
# 进入后端目录
cd E:\project\lean\MuMuAINovel\MuMuAINovel\backend

# 激活虚拟环境
.venv\Scripts\activate

# 设置环境变量
$env:PYTHONPATH="E:\project\lean\MuMuAINovel\MuMuAINovel\backend"

# 启动服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 方式 2: PowerShell 脚本启动

创建 `start.ps1`：

```powershell
# start.ps1
$ErrorActionPreference = "Stop"

# 进入项目目录
$projectPath = "E:\project\lean\MuMuAINovel\MuMuAINovel\backend"
Set-Location $projectPath

# 激活虚拟环境
& "$projectPath\.venv\Scripts\Activate.ps1"

# 设置环境变量
$env:PYTHONPATH = $projectPath

# 查找可用端口
$port = 8000
while (Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue) {
    $port++
}

Write-Host "启动 MuMuAINovel 服务..."
Write-Host "访问地址: http://localhost:$port"

# 启动服务
python -m uvicorn app.main:app --host 0.0.0.0 --port $port --reload
```

运行：
```powershell
.\start.ps1
```

### 停止服务

#### 方式 1: 通过 PID

```powershell
# 查找进程
Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess

# 停止进程
Stop-Process -Id <PID> -Force
```

#### 方式 2: 通过端口

```powershell
# 停止占用 8000 端口的进程
Get-NetTCPConnection -LocalPort 8000 | ForEach-Object { 
    Stop-Process -Id $_.OwningProcess -Force 
}
```

#### 方式 3: 停止所有 Python 进程

```powershell
# 停止所有 uvicorn 进程
Get-Process | Where-Object { $_.CommandLine -like '*uvicorn*' } | Stop-Process -Force
```

---

## 🔧 日常维护

### 查看服务状态

```powershell
# 检查端口监听
Get-NetTCPConnection | Where-Object { $_.LocalPort -eq 8000 }

# 检查进程
Get-Process | Where-Object { $_.ProcessName -eq 'python' -and $_.CommandLine -like '*uvicorn*' }

# 测试健康检查
Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing
```

### 查看日志

```powershell
# 实时查看日志
Get-Content backend/logs/app.log -Tail 50 -Wait

# 查看最近 100 行
Get-Content backend/logs/app.log -Tail 100

# 搜索错误
Select-String -Path backend/logs/app.log -Pattern "ERROR"
```

### 重启服务

```powershell
# 一键重启脚本
$port = 8000

# 停止旧服务
Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.OwningProcess -Force
}
Start-Sleep -Seconds 2

# 启动新服务
cd E:\project\lean\MuMuAINovel\MuMuAINovel\backend
$env:PYTHONPATH = "E:\project\lean\MuMuAINovel\MuMuAINovel\backend"
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port $port
```

### 更新项目

```bash
# 拉取最新代码
git pull origin main

# 更新后端依赖
cd backend
pip install -r requirements.txt --upgrade

# 更新前端依赖
cd ../frontend
npm install
npm run build

# 重启服务
# (使用上面的重启脚本)
```

### 备份数据

```powershell
# 备份数据库（PostgreSQL）
$backupPath = "E:\backups\mumuai_novel_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql"
pg_dump -h localhost -U mumuai -d mumuai_novel -f $backupPath

# 备份 SQLite
Copy-Item backend/mumuai_novel.db "E:\backups\mumuai_novel_$(Get-Date -Format 'yyyyMMdd_HHmmss').db"
```

---

## 🐛 故障排查

### 问题 1: 端口被占用

**症状**：`[WinError 10048] 通常每个套接字地址只能使用一次`

**解决**：
```powershell
# 查找占用端口的进程
Get-NetTCPConnection -LocalPort 8000

# 停止进程
Stop-Process -Id <PID> -Force

# 或使用其他端口
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### 问题 2: Python 3.13 兼容性问题

**症状**：`AssertionError: Class SQLCoreOperations directly inherits TypingOnly`

**解决**：
```bash
pip install --upgrade sqlalchemy fastapi pydantic uvicorn
```

### 问题 3: 数据库连接失败

**症状**：`DB_ERROR: [WinError 1225] 远程计算机拒绝网络连接`

**解决**：
1. 检查 PostgreSQL 服务是否运行
2. 检查数据库配置是否正确
3. 检查防火墙设置
4. 使用 SQLite 临时方案

### 问题 4: 前端构建失败

**症状**：`Cannot find module 'dagre'`

**解决**：
```bash
cd frontend
npm install dagre @xyflow/react --save
npm run build
```

### 问题 5: Embedding 模型加载失败

**症状**：模型文件不存在或加载失败

**解决**：
1. 检查 `backend/embedding/` 目录
2. 确保模型文件存在：
   - `models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2/`
3. 如需下载模型，加入项目 QQ 群获取

---

## 📞 技术支持

- **GitHub Issues**: https://github.com/xiamuceer-j/MuMuAINovel/issues
- **Linux DO**: https://linux.do/t/topic/1106333
- **QQ 交流群**: 见项目主页二维码

---

## 📝 更新日志

| 日期 | 版本 | 更新内容 |
|------|------|---------|
| 2026-03-08 | 1.3.8 | 修复 3 个关键问题：.env 编码、前端编码、数据库字段缺失 |
| 2026-03-08 | 1.3.6 | 初始部署，配置 Neon 数据库 |

---

## 🔧 2026-03-08 问题修复记录

### 问题 1: .env 文件编码错误

**症状**：中文注释显示乱码

**原因**：文件保存为 ANSI 编码而非 UTF-8

**解决**：
```python
# 使用 Python 脚本批量转换
import chardet

def fix_encoding(file_path):
    with open(file_path, 'rb') as f:
        raw = f.read()
    result = chardet.detect(raw)
    if result['encoding'] != 'utf-8':
        content = raw.decode(result['encoding'])
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
```

### 问题 2: 前端 TypeScript 文件编码问题

**症状**：`npm run build` 失败，数百个 TypeScript 错误

**解决**：
```bash
cd frontend

# 安装 chardet
pip install chardet

# 使用 Python 脚本检测和转换编码
python fix_encoding.py

# 重新构建
npm run build
```

**构建结果**：
- ✅ 3671 个模块转换成功
- ✅ 输出文件：
  - `backend/static/index.html` (0.81 KB)
  - `backend/static/assets/index-DlX2FZpf.js` (858.46 KB)
  - `backend/static/assets/vendor-antd-De_nAUwb.js` (1,203.98 KB)
  - `backend/static/assets/vendor-react-BEIWTLWi.js` (163.47 KB)

### 问题 3: 数据库字段缺失

**症状**：
```
sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError: 
column "status" of relation "characters" does not exist
```

**解决**：使用 Node.js/pg 直接执行 ALTER TABLE
```javascript
const { Client } = require('pg');
const client = new Client({ connectionString: process.env.DATABASE_URL });
await client.connect();

await client.query(`
  ALTER TABLE characters 
  ADD COLUMN IF NOT EXISTS status VARCHAR(50),
  ADD COLUMN IF NOT EXISTS status_changed_chapter VARCHAR(100),
  ADD COLUMN IF NOT EXISTS current_state VARCHAR(255);
`);
```

### 问题 4: Python 依赖缺失 / Pylance 导入错误

**症状**：Pylance 报告 `无法解析导入"psycopg"` 和 `无法解析导入"chardet"`

**原因**：VS Code 没有使用项目虚拟环境的 Python 解释器

**解决步骤**：

1. **安装依赖**：
```bash
cd backend
.venv\Scripts\pip.exe install psycopg2-binary
.venv\Scripts\pip.exe install chardet
```

2. **配置 VS Code Python 解释器**：
   - 按 `Ctrl+Shift+P`
   - 输入 `Python: Select Interpreter`
   - 选择 `./backend/.venv/Scripts/python.exe`

3. **或创建 `.vscode/settings.json`**：
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/.venv/Scripts/python.exe",
  "python.analysis.extraPaths": [
    "${workspaceFolder}/backend/.venv/Lib/site-packages"
  ]
}
```

4. **重启 VS Code** 或 Pylance 语言服务器

---

## ✅ 当前部署状态（2026-03-08 20:24）

| 组件 | 状态 | 详情 |
|------|------|------|
| **后端服务** | ✅ 运行中 | PID 23388, 端口 8002 |
| **前端构建** | ✅ 成功 | 3671 模块，构建时间 13.91s |
| **数据库连接** | ✅ 正常 | Neon PostgreSQL |
| **Embedding 模型** | ✅ 已加载 | paraphrase-multilingual-MiniLM-L12-v2 |
| **静态文件** | ✅ 已生成 | backend/static/ |
| **Python 依赖** | ✅ 完整 | psycopg2-binary, chardet 已安装 |

**访问地址**：
- 前端：http://localhost:8002
- API 文档：http://localhost:8002/docs
- 健康检查：http://localhost:8002/api/health

---

**文档生成时间**: 2026-03-08 20:24  
**维护者**: OpenClaw Assistant (小欧)  
**状态**: ✅ 所有问题已解决，服务正常运行
