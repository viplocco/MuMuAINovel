# MuMuAINovel 启动指南

> 本文档记录项目的快速启动步骤
> 生成时间：2026-04-22

---

## 快速启动

### 方式一：Docker 部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/xiamuceer-j/MuMuAINovel.git
cd MuMuAINovel

# 2. 配置环境变量
cp backend/.env.example .env
# 编辑 .env 填入 API 密钥和数据库配置

# 3. 启动服务
docker-compose up -d

# 4. 验证服务状态
docker ps
# 应该看到 mumuainovel 和 mumuainovel-postgres 两个容器

# 5. 访问服务
curl http://localhost:8000/health
# 返回 {"status":"ok"} 表示启动成功
```

### 方式二：本地开发

#### 1. 检查端口占用

```powershell
# 检查端口占用
netstat -ano | findstr :8002

# 检查 Python 进程
tasklist | findstr python
```

#### 2. 启动 PostgreSQL

```powershell
# 使用 Docker 启动 PostgreSQL
docker run -d --name mumuainovel-postgres `
  -e POSTGRES_DB=mumuai_novel `
  -e POSTGRES_USER=mumuai `
  -e POSTGRES_PASSWORD=123456 `
  -p 5432:5432 `
  postgres:18-alpine
```

#### 3. 启动后端服务

```powershell
# 进入后端目录
cd E:\project\lean\MuMuAINovel\MuMuAINovel\backend

# 激活虚拟环境
.venv\Scripts\activate

# 设置环境变量
$env:PYTHONPATH="E:\project\lean\MuMuAINovel\MuMuAINovel\backend"

# 启动服务（端口 8002）
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

#### 4. 启动前端服务

```powershell
# 进入前端目录
cd E:\project\lean\MuMuAINovel\MuMuAINovel\frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

#### 5. 验证启动成功

启动日志应显示：
```
INFO:     Uvicorn running on http://0.0.0.0:8002 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxx] using WatchFiles
INFO:     root - 日志文件输出已启用: logs/app.log
```

### 访问地址

| 地址 | 说明 |
|------|------|
| http://localhost:8002 | 前端页面（本地开发） |
| http://localhost:8000 | 前端页面（Docker 部署） |
| http://localhost:8002/docs | API 文档 (Swagger) |
| http://localhost:8000/docs | API 文档 (Swagger, Docker) |
| http://localhost:8000/api/health | 健康检查 (Docker) |

默认账户：admin / admin123

---

## Docker 常用命令

```bash
# 查看容器状态
docker ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 进入容器
docker exec -it mumuainovel /bin/bash

# 查看资源使用
docker stats
```

---

## 常见问题

### 端口被占用

```powershell
# 查找占用端口的进程
Get-NetTCPConnection -LocalPort 8002

# 停止进程
Stop-Process -Id <PID> -Force
```

### 虚拟环境未激活

如果看到 `ModuleNotFoundError`，请确保已激活虚拟环境：
```powershell
.venv\Scripts\activate
```

### 环境变量未设置

如果看到导入错误，请设置 PYTHONPATH：
```powershell
$env:PYTHONPATH="E:\project\lean\MuMuAINovel\MuMuAINovel\backend"
```

### 数据库连接失败

确保 PostgreSQL 容器正在运行：
```bash
docker ps | grep postgres
```

---

## 项目结构

```
MuMuAINovel/
├── backend/          # FastAPI 后端 (Python 3.11+)
│   ├── app/         # 应用代码
│   │   ├── api/     # 27+ API 路由
│   │   ├── models/  # 35+ 数据模型
│   │   ├── services/# 业务逻辑
│   │   └── mcp/     # MCP 工具集成
│   ├── .venv/       # Python 虚拟环境
│   ├── logs/        # 日志文件
│   ├── scripts/     # 工具脚本
│   └── static/      # 前端构建产物
├── frontend/        # React 前端
│   ├── src/         # 源代码
│   │   ├── pages/  # 28+ 页面组件
│   │   ├── components/
│   │   └── store/  # Zustand 状态管理
│   └── dist/        # 构建产物
├── docker-compose.yml
├── Dockerfile
├── STARTUP.md       # 本文档
├── DEPLOYMENT.md    # 部署文档
└── CLAUDE.md        # 开发指南
```

---

## 相关文档

- [部署文档](./DEPLOYMENT.md) - 详细部署步骤和配置
- [CLAUDE.md](./CLAUDE.md) - 开发指南和架构说明
- [README.md](./README.md) - 项目介绍

---

**维护者**: OpenClaw Assistant (小欧)
**最后更新**: 2026-04-22