# 数据浏览系统

基于Web的多用户数据浏览系统，支持文件系统、数据库、对象存储等多种数据源类型的统一浏览和管理。

## 技术架构

- **前端**: Vue 3 + Vite + Element Plus + TypeScript
- **后端**: Python + FastAPI + SQLAlchemy + Pydantic
- **数据库**: SQLite/PostgreSQL/MySQL
- **缓存**: Redis（可选）
- **容器化**: Docker + Docker Compose

## 功能特性

### 核心模块

1. **数据源管理模块**
   - 支持文件系统、数据库、对象存储三种数据源类型
   - 提供数据源的增删改查操作
   - 连接配置管理和测试功能

2. **文件系统浏览模块**
   - 树状目录结构展示
   - 文件预览和下载功能
   - 支持多种文件格式

3. **数据库浏览模块**
   - 支持MySQL、PostgreSQL、SQLite等主流数据库
   - 表结构查看和数据浏览
   - 基础的CRUD操作

4. **对象存储浏览模块**
   - 支持AWS S3、MinIO等对象存储
   - 文件上传、下载功能
   - 预签名URL生成

5. **Dashboard仪表盘**
   - 数据源概览和统计
   - 系统使用情况监控

6. **用户权限管理**
   - 用户注册/登录
   - 角色权限控制（管理员/普通用户）
   - 用户管理界面

### 技术特性

- 响应式设计，支持移动端
- JWT认证和权限控制
- RESTful API设计
- 数据源连接池管理
- 异常处理和日志记录
- Docker容器化部署

## 快速开始

### 环境要求

- Node.js 18+
- Python 3.11+
- Docker & Docker Compose（可选）

### 开发环境搭建

#### 1. 克隆项目

```bash
git clone <repository-url>
cd data-browser
```

#### 2. 前端启动

```bash
# 安装依赖
npm install
# 或使用pnpm
pnpm install

# 启动开发服务器
npm run dev
# 访问 http://localhost:5173
```

#### 3. 后端启动

```bash
cd backend

# 安装Python依赖
pip install -r requirements.txt

# 设置环境变量（复制并修改配置文件）
cp .env.example .env

# 启动后端服务
python main.py
# 访问 http://localhost:8000
```

### Docker部署

#### 开发环境

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

#### 生产环境

```bash
# 使用生产环境配置
docker-compose --profile production up -d
```

### 环境变量配置

主要环境变量说明：

```bash
# 服务配置
ENVIRONMENT=development
HOST=0.0.0.0
PORT=8000

# 数据库配置
DATABASE_URL=sqlite:///./data-browser.db
# DATABASE_URL=postgresql://user:pass@localhost:5432/db_name

# JWT密钥（生产环境必须修改）
SECRET_KEY=your-secret-key-min-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS配置
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

## API文档

启动后端服务后，访问以下地址查看API文档：

- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## 项目结构

```
data-browser/
├── src/                        # 前端源码
│   ├── components/            # Vue组件
│   ├── views/                # 页面视图
│   ├── stores/               # Pinia状态管理
│   ├── router/               # 路由配置
│   ├── api/                  # API接口
│   ├── types/                # TypeScript类型定义
│   └── utils/                # 工具函数
├── backend/                    # 后端源码
│   ├── app/
│   │   ├── api/              # API路由
│   │   ├── core/             # 核心配置
│   │   ├── models/           # 数据模型
│   │   ├── schemas/          # Pydantic模式
│   │   ├── services/         # 业务逻辑
│   │   └── utils/            # 工具函数
│   ├── requirements.txt      # Python依赖
│   └── main.py              # 应用入口
├── docker-compose.yml          # Docker编排
├── package.json               # 前端依赖配置
└── README.md                  # 项目文档
```

## 数据源配置示例

### 文件系统

```json
{
  "type": "filesystem",
  "config": {
    "path": "/data/files",
    "encoding": "utf-8",
    "extensions": [".txt", ".csv", ".json"]
  }
}
```

### 数据库

```json
{
  "type": "database", 
  "config": {
    "db_type": "MySQL",
    "host": "localhost",
    "port": 3306,
    "database": "test_db",
    "user": "username",
    "password": "password"
  }
}
```

### 对象存储

```json
{
  "type": "object_storage",
  "config": {
    "bucket": "my-bucket",
    "endpoint": "https://s3.amazonaws.com", 
    "access_key": "ACCESS_KEY",
    "secret_key": "SECRET_KEY",
    "region": "us-east-1"
  }
}
```

## 开发指南

### 添加新的数据源类型

1. 在`backend/app/models/datasource.py`中添加新的数据源类型枚举
2. 创建对应的配置Schema类
3. 实现数据源连接器和浏览器逻辑
4. 在前端添加相应的配置表单和浏览界面

### 自定义权限控制

可以在`backend/app/core/security.py`中自定义权限验证逻辑，支持更细粒度的权限控制。

## 贡献指南

1. Fork项目
2. 创建功能分支: `git checkout -b feature/new-feature`
3. 提交更改: `git commit -am 'Add new feature'`
4. 推送分支: `git push origin feature/new-feature`
5. 提交Pull Request

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交Issue或联系开发团队。
