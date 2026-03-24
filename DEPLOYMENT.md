# 🚀 NL2MQL2SQL 部署完整指南

## 📋 目录

- [快速选择](#快速选择)
- [方案一：Docker 部署（推荐）](#方案一docker-部署推荐)
  - [开发环境](#开发环境)
  - [生产环境](#生产环境)
- [方案二：本地部署](#方案二本地部署)
  - [手动启动](#手动启动)
  - [一键启动](#一键启动)
- [配置说明](#配置说明)
- [访问地址](#访问地址)
- [常见问题](#常见问题)
- [高级配置](#高级配置)

---

## 🎯 快速选择

| 部署方案 | 适用场景 | 优点 | 启动时间 |
|---------|---------|------|---------|
| **Docker 开发环境** | Docker 环境、快速开发 | 一键启动、代码热重载、环境隔离 | ~3 分钟 |
| **Docker 生产环境** | 服务器部署、生产环境 | 优化镜像、Nginx 代理、健康检查 | ~5 分钟 |
| **本地部署** | 本机开发、无 Docker | 无需 Docker、快速启动 | ~2 分钟 |

**推荐**：
- 🚀 **新手推荐**：Docker 开发环境（一键启动）
- 🏭 **生产环境**：Docker 生产环境
- 💻 **开发者**：本地部署（可选）

---

## 方案一：Docker 部署（推荐）

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+

### 环境检查

```bash
# Windows
docker-check.bat

# Linux/Mac
chmod +x docker-check.sh && ./docker-check.sh
```

### 一键启动

```bash
# Windows
docker-start.bat

# Linux/Mac
chmod +x docker-start.sh && ./docker-start.sh
```

脚本会提示选择部署模式：
- **1) 开发环境** - 代码热重载
- **2) 生产环境** - 优化镜像

---

### 开发环境

#### 特点

- ✅ 代码热重载（修改代码自动生效）
- ✅ 挂载本地代码目录
- ✅ Vite Dev Server + Uvicorn Reload
- ✅ 适合日常开发

#### 启动步骤

**方式一：使用启动脚本**
```bash
# 运行启动脚本，选择 1（开发环境）
docker-start.bat    # Windows
./docker-start.sh    # Linux/Mac
```

**方式二：手动启动**
```bash
# 使用开发环境配置
docker-compose -f docker-compose.dev.yml up -d

# 查看日志
docker-compose -f docker-compose.dev.yml logs -f
```

#### 访问地址

| 服务 | 地址 |
|------|------|
| 前端应用 | http://localhost:5173 |
| 后端 API | http://localhost:8011 |
| API 文档 | http://localhost:8011/docs |
| 数据库 | localhost:3306 |

#### 开发流程

1. **修改代码**：直接编辑 `frontend/` 或 `backend/` 目录
2. **自动重载**：
   - 前端：Vite 自动检测文件变化
   - 后端：Uvicorn 的 `--reload` 自动重载
3. **查看日志**：`docker-compose -f docker-compose.dev.yml logs -f`

#### 停止服务

```bash
docker-compose -f docker-compose.dev.yml down

# 停止并删除数据卷
docker-compose -f docker-compose.dev.yml down -v
```

---

### 生产环境

#### 特点

- ✅ 多阶段构建（镜像体积优化）
- ✅ Nginx 反向代理
- ✅ 健康检查（自动恢复）
- ✅ 数据持久化
- ✅ 自动重启策略

#### 启动步骤

**方式一：使用启动脚本**
```bash
# 运行启动脚本，选择 2（生产环境）
docker-start.bat    # Windows
./docker-start.sh    # Linux/Mac
```

**方式二：手动启动**

```bash
# 1. 配置环境变量
cp .env.docker .env
nano .env  # 编辑配置

# 2. 构建镜像
docker-compose build

# 3. 启动服务
docker-compose up -d

# 4. 查看状态
docker-compose ps
```

#### 环境变量配置

**必须修改的配置**：
```env
# 数据库密码（生产环境必须修改）
DB_PASSWORD=your-strong-password-here

# 安全密钥（生产环境必须修改）
SECRET_KEY=your-production-secret-key-min-32-chars
ENCRYPTION_KEY=your-encryption-key-32bytes-long
```

**可选配置**：
```env
# 端口配置
FRONTEND_PORT=80
BACKEND_PORT=8011
DB_PORT=3306

# 调试模式
DEBUG=False

# LLM 配置
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-4-turbo
# DEFAULT_LLM_API_KEY=sk-xxx
```

#### 访问地址

| 服务 | 地址 |
|------|------|
| 前端应用 | http://localhost |
| 后端 API | http://localhost:8011 |
| API 文档 | http://localhost:8011/docs |
| 数据库 | localhost:3306 |

#### 停止服务

```bash
# 停止容器
docker-compose stop

# 停止并删除容器
docker-compose down

# 停止并删除容器 + 数据卷
docker-compose down -v
```

---

## 方案二：本地部署

### 前置要求

- **Python**: 3.11+
- **Node.js**: 18+
- **数据库**: MySQL 8.0+ 或 PostgreSQL 12+

### 一键启动

**Windows**：
```bash
# 双击运行
start.bat

# 或命令行运行
start.bat
```

**Linux/Mac**：
```bash
chmod +x start.sh
./start.sh
```

### 手动启动

#### 后端启动

```bash
cd backend

# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
# Windows
copy .env.example .env
# Linux/Mac
cp .env.example .env

# 3. 编辑 .env 文件
nano .env  # 配置数据库连接
# DATABASE_URL=mysql+pymysql://root:password@localhost:3306/nlqdb

# 4. 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8011 --reload
```

#### 前端启动

```bash
cd frontend

# 1. 安装依赖
npm install

# 2. 配置环境变量
# Windows
copy .env.example .env
# Linux/Mac
cp .env.example .env

# 3. 启动服务
npm run dev
```

### 访问地址

| 访问方式 | 前端应用 | 后端 API | API 文档 |
|----------|----------|----------|----------|
| 本地访问 | http://localhost:5173 | http://localhost:8011 | http://localhost:8011/docs |
| 内网访问 | http://192.168.x.x:5173 | http://192.168.x.x:8011 | http://192.168.x.x:8011/docs |

### 获取本机 IP

```bash
# Windows
get-ip.bat

# Linux/Mac
./get-ip.sh

# 或直接运行 Python 脚本
python get-ip.py
```

### 停止服务

**Windows**：
```bash
stop.bat
```

**Linux/Mac**：
```bash
./stop.sh
```

---

## 📊 访问地址汇总

### Docker 开发环境

| 服务 | 本地访问 | 内网访问 |
|------|----------|----------|
| 前端 | http://localhost:5173 | http://192.168.x.x:5173 |
| 后端 API | http://localhost:8011 | http://192.168.x.x:8011 |
| API 文档 | http://localhost:8011/docs | http://192.168.x.x:8011/docs |

### Docker 生产环境

| 服务 | 本地访问 | 内网访问 |
|------|----------|----------|
| 前端 | http://localhost | http://192.168.x.x |
| 后端 API | http://localhost:8011 | http://192.168.x.x:8011 |
| API 文档 | http://localhost:8011/docs | http://192.168.x.x:8011/docs |

### 本地部署

| 服务 | 本地访问 | 内网访问 |
|------|----------|----------|
| 前端 | http://localhost:5173 | http://192.168.x.x:5173 |
| 后端 API | http://localhost:8011 | http://192.168.x.x:8011 |
| API 文档 | http://localhost:8011/docs | http://192.168.x.x:8011/docs |

---

## ⚙️ 配置说明

### 后端配置 (`backend/.env`)

| 变量名 | 必需 | 默认值 | 说明 |
|--------|------|--------|------|
| `DATABASE_URL` | ✅ | - | 数据库连接字符串 |
| `APP_NAME` | ❌ | NL2MQL2SQL | 应用名称 |
| `DEBUG` | ❌ | True | 调试模式 |
| `SECRET_KEY` | ✅* | your-secret-key | JWT 密钥（生产环境必须修改） |
| `ENCRYPTION_KEY` | ✅* | your-encryption-key | 加密密钥（生产环境必须修改） |

\* 生产环境必须修改

**数据库连接示例**：
```env
# MySQL
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/nlqdb?charset=utf8mb4

# PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/nlqdb

# SQLite（开发测试）
DATABASE_URL=sqlite:///./data.db
```

### 前端配置 (`frontend/.env`)

| 变量名 | 推荐值 | 说明 |
|--------|--------|------|
| `VITE_API_BASE_URL` | `/api/v1` | API 基础路径（相对路径） |

**三种配置方案**：

| 方案 | 配置值 | 适用场景 |
|------|--------|----------|
| 方案一（推荐） | `/api/v1` | 任何环境，通过 Vite Proxy 转发 |
| 方案二 | `http://localhost:8011/api/v1` | 仅本地开发 |
| 方案三 | `http://192.168.1.100:8011/api/v1` | 特定内网环境 |

### CORS 配置

后端启动时会自动添加当前内网 IP 到 CORS 允许列表，无需手动配置。

查看启动日志确认：
```
[CORS] 允许的源地址：
  - http://localhost:5173
  - http://127.0.0.1:5173
  - http://192.168.1.100:5173  (自动添加)
  - *
```

---

## ❓ 常见问题

### Docker 部署问题

#### 1. 端口被占用

**错误信息**：
```
Bind for 0.0.0.0:80 failed: port is already allocated
```

**解决方案**：

修改 `.env` 文件：
```env
FRONTEND_PORT=8080
BACKEND_PORT=9011
DB_PORT=3307
```

---

#### 2. 数据库连接失败

**错误信息**：
```
Can't connect to MySQL server on 'db:3306'
```

**解决方案**：

```bash
# 查看数据库日志
docker-compose logs db

# 等待数据库启动
sleep 10
docker-compose up -d backend
```

---

#### 3. 镜像构建失败

**错误信息**：
```
ERROR [build] failed to compute cache key
```

**解决方案**：

```bash
# 清理缓存
docker system prune -a

# 重新构建
docker-compose build --no-cache
```

---

### 本地部署问题

#### 1. 后端启动失败

**检查项**：
```bash
# 检查端口占用
netstat -ano | findstr :8011  # Windows
lsof -i :8011              # Linux/Mac

# 检查依赖安装
pip list | findstr fastapi
```

**解决方案**：
- 更换端口：`uvicorn app.main:app --port 9011`
- 重新安装依赖：`pip install -r requirements.txt`

---

#### 2. 前端启动失败

**检查项**：
```bash
# 检查 Node.js 版本
node --version  # 需要 18+

# 检查依赖安装
npm list
```

**解决方案**：
```bash
# 清理缓存
npm cache clean --force

# 重新安装
rm -rf node_modules
npm install
```

---

#### 3. 内网其他电脑无法访问

**检查项**：

1. **防火墙设置**
   ```bash
   # Windows 防火墙
   # 控制面板 → 系统和安全 → Windows Defender 防火墙
   # 允许应用通过防火墙 → 添加 uvicorn 和 node.exe

   # Linux 防火墙
   sudo ufw allow 5173/tcp
   sudo ufw allow 8011/tcp
   ```

2. **服务监听地址**
   - 前端：确认 `vite.config.ts` 中 `host: '0.0.0.0'`
   - 后端：确认 uvicorn 启动时使用 `--host 0.0.0.0`

3. **网络连接**
   - 确认电脑在同一局域网
   - 测试网络连通性：`ping 192.168.1.100`

---

#### 4. API 请求 CORS 错误

**错误信息**：
```
Access to XMLHttpRequest has been blocked by CORS policy
```

**解决方案**：

检查后端启动日志，确认当前 IP 已添加到 CORS 允许列表：
```
[CORS] 允许的源地址：
  - http://localhost:5173
  - http://192.168.1.100:5173  # 确认有这一行
```

如果仍然失败，检查前端 API 配置：
```javascript
// frontend/.env
VITE_API_BASE_URL=/api/v1  // 使用相对路径
```

---

## 🔧 高级配置

### 1. 更换端口

#### Docker 环境

修改 `.env` 文件：
```env
FRONTEND_PORT=3000
BACKEND_PORT=9000
DB_PORT=3307
```

修改 Nginx 配置（`frontend/nginx.conf`）：
```nginx
upstream backend {
    server backend:9000;
}
```

重新启动：
```bash
docker-compose down
docker-compose up -d
```

#### 本地环境

**修改前端端口**（`frontend/vite.config.ts`）：
```typescript
server: {
  host: '0.0.0.0',
  port: 3000,
}
```

**修改后端端口**：
```bash
uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload
```

---

### 2. 使用不同的数据库

#### Docker 环境

修改 `docker-compose.yml` 中的数据库服务：
```yaml
services:
  db:
    image: postgres:15  # 使用 PostgreSQL
    environment:
      POSTGRES_PASSWORD: password
      POSTGRES_DB: nlqdb
```

修改后端环境变量：
```env
DATABASE_URL=postgresql://root:password@db:5432/nlqdb
```

#### 本地环境

修改 `backend/.env`：
```env
# PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/nlqdb

# MySQL
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/nlqdb
```

安装对应的数据库驱动：
```bash
# PostgreSQL
pip install psycopg2-binary

# MySQL
pip install pymysql
```

---

### 3. 配置 LLM API

**前端配置**（系统设置 → 模型配置）：
- LLM Provider: OpenAI / Ollama / Azure / Claude
- API Key: 对应平台的 API Key
- Base URL: 自定义 API 端点（可选）

**后端配置**（`backend/.env`）：
```env
# OpenAI
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_API_KEY=sk-xxx
DEFAULT_LLM_MODEL=gpt-4-turbo
DEFAULT_LLM_API_BASE=https://api.openai.com/v1

# Ollama
DEFAULT_LLM_PROVIDER=ollama
DEFAULT_LLM_MODEL=llama2
DEFAULT_LLM_API_BASE=http://localhost:11434
```

---

### 4. Docker 数据备份

#### 备份数据

```bash
# MySQL 备份
docker-compose exec -T db mysqldump -uroot -p${DB_PASSWORD} ${DB_NAME} \
  > backup_$(date +%Y%m%d_%H%M%S).sql

# 查看备份
ls -lh backup_*.sql
```

#### 恢复数据

```bash
# 恢复数据
cat backup_20260324_120000.sql | \
  docker-compose exec -T db mysql -uroot -p${DB_PASSWORD} ${DB_NAME}
```

#### 自动备份脚本

创建 `backup.sh`：
```bash
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="nlqdb"
DB_PASSWORD="123456"

mkdir -p ${BACKUP_DIR}

docker-compose exec -T db mysqldump -uroot -p${DB_PASSWORD} ${DB_NAME} \
  > ${BACKUP_DIR}/backup_${DATE}.sql

# 保留最近 7 天的备份
find ${BACKUP_DIR} -name "backup_*.sql" -mtime +7 -delete

echo "Backup completed: backup_${DATE}.sql"
```

添加定时任务：
```bash
# 编辑 crontab
crontab -e

# 每天凌晨 2 点备份
0 2 * * * /path/to/backup.sh
```

---

### 5. Nginx 反向代理（生产环境）

#### 自定义域名配置

修改 `frontend/nginx.conf`：
```nginx
server {
    listen 80;
    server_name your-domain.com;  # 修改为你的域名

    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:8011;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### SSL/HTTPS 配置

使用 Let's Encrypt 免费证书：

```bash
# 安装 certbot
docker run -it --rm \
  -v /etc/letsencrypt:/etc/letsencrypt \
  certbot/certbot certonly --standalone -d your-domain.com
```

修改 Nginx 配置：
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # ... 其他配置
}

# HTTP 跳转 HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

---

### 6. 监控和日志

#### 查看日志

**Docker 环境**：
```bash
# 所有服务日志
docker-compose logs -f

# 特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 最近 100 行日志
docker-compose logs --tail=100 backend
```

**本地环境**：
```bash
# 后端日志
tail -f backend/logs/app.log

# 前端日志
# 在浏览器控制台查看
```

#### 监控服务

使用 Docker Stats：
```bash
docker stats
```

查看容器资源使用情况（CPU、内存、网络、磁盘）。

---

## 📞 技术支持

### 获取帮助

1. **查看日志**：
   - Docker: `docker-compose logs -f`
   - 本地: `backend/logs/app.log`

2. **检查配置**：
   - Docker: `docker-compose config`
   - 本地: 检查 `.env` 文件

3. **提交 Issue**：项目仓库

### 有用的链接

- **Docker 官方文档**：https://docs.docker.com/
- **FastAPI 文档**：https://fastapi.tiangolo.com/
- **Vue 3 文档**：https://vuejs.org/
- **项目架构**：[ARCHITECTURE_SUMMARY.md](./ARCHITECTURE_SUMMARY.md)

---

## 🎉 总结

### 部署方案对比

| 特性 | Docker 开发 | Docker 生产 | 本地部署 |
|------|------------|------------|---------|
| 一键启动 | ✅ | ✅ | ✅ |
| 代码热重载 | ✅ | ❌ | ✅ |
| 环境隔离 | ✅ | ✅ | ❌ |
| 生产级优化 | ❌ | ✅ | ❌ |
| 需要安装 Docker | ✅ | ✅ | ❌ |
| 启动时间 | ~3 分钟 | ~5 分钟 | ~2 分钟 |

### 推荐使用场景

- **新手/快速体验**：Docker 开发环境（一键启动）
- **生产部署**：Docker 生产环境（优化镜像）
- **日常开发**：本地部署（可选 Docker）
- **内网分享**：任意方案（都支持内网访问）

---

**选择适合你的部署方案，立即开始使用！** 🚀

---

**文档版本**: v2.0
**最后更新**: 2026-03-24
