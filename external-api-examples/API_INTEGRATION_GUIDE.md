# 数据浏览系统 API 接入指南

## 📌 概述

本指南为外部系统提供完整的API接入方案，支持通过RESTful API访问数据浏览系统的所有功能。

## 🌐 基础信息

- **API基础地址**: `http://localhost:8000/api/v1`
- **认证方式**: JWT Bearer Token
- **数据格式**: JSON
- **字符编码**: UTF-8

## 📚 API文档

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## 🔐 认证流程

### 1. 用户登录

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

**响应示例**:
```json
{
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "bearer",
    "expires_in": 1800,
    "user": {
      "id": "user_id",
      "username": "username",
      "name": "用户姓名",
      "role": "admin"
    }
  },
  "message": "登录成功",
  "success": true,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### 2. 使用Token

在所有后续请求中添加Authorization头：

```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

### 3. 刷新Token

```http
POST /api/v1/auth/refresh
Content-Type: application/json
Authorization: Bearer {refresh_token}

{
  "refreshToken": "refresh_token_here"
}
```

## 📊 核心API接口

### 数据源管理

#### 1. 获取数据源列表

```http
GET /api/v1/datasources?page=1&limit=20&type=filesystem&is_active=true&search=keyword
Authorization: Bearer {token}
```

**查询参数**:
- `page`: 页码 (默认: 1)
- `limit`: 每页数量 (默认: 20, 最大: 100)
- `type`: 数据源类型 (`filesystem`|`database`|`object_storage`)
- `is_active`: 是否激活 (`true`|`false`)
- `search`: 搜索关键词

**响应示例**:
```json
{
  "data": [
    {
      "id": "ds_001",
      "name": "test_fs",
      "cname": "测试文件系统",
      "type": "filesystem",
      "desc": "用于测试的本地文件系统",
      "company": "测试公司",
      "is_active": true,
      "is_connected": true,
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 20,
  "pages": 1,
  "message": "获取数据源列表成功",
  "success": true
}
```

#### 2. 获取数据源详情

```http
GET /api/v1/datasources/{datasource_id}
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "data": {
    "id": "ds_001",
    "name": "test_fs",
    "cname": "测试文件系统",
    "type": "filesystem",
    "desc": "用于测试的本地文件系统",
    "company": "测试公司",
    "config": {
      "path": "/data/test",
      "encoding": "utf-8",
      "extensions": [".txt", ".csv", ".json"]
    },
    "extra_metadata": {},
    "is_active": true,
    "is_connected": true,
    "size": 1024000,
    "num": 150,
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z"
  },
  "message": "获取数据源信息成功",
  "success": true
}
```

#### 3. 获取数据源统计

```http
GET /api/v1/datasources/statistics
Authorization: Bearer {token}
```

### 数据浏览

#### 1. 文件系统浏览

```http
GET /api/v1/browse/filesystem/{datasource_id}/files?path=/data/folder
Authorization: Bearer {token}
```

**查询参数**:
- `path`: 文件路径 (默认: "/")

**响应示例**:
```json
{
  "data": [
    {
      "name": "document.txt",
      "path": "/data/folder/document.txt",
      "type": "file",
      "size": 1024,
      "modified_time": "2024-01-01T12:00:00Z",
      "is_directory": false,
      "extension": ".txt",
      "mime_type": "text/plain"
    },
    {
      "name": "subfolder",
      "path": "/data/folder/subfolder",
      "type": "directory",
      "size": 0,
      "modified_time": "2024-01-01T10:00:00Z",
      "is_directory": true
    }
  ],
  "message": "获取文件列表成功",
  "success": true
}
```

#### 2. 数据库表浏览

```http
GET /api/v1/browse/database/{datasource_id}/tables?database=test_db
Authorization: Bearer {token}
```

**查询参数**:
- `database`: 数据库名称 (可选)

**响应示例**:
```json
{
  "data": [
    {
      "name": "users",
      "schema": "public",
      "type": "table",
      "rows": 1000,
      "size": "64 kB",
      "comment": "用户表"
    },
    {
      "name": "orders",
      "schema": "public", 
      "type": "table",
      "rows": 5000,
      "size": "320 kB",
      "comment": "订单表"
    }
  ],
  "message": "获取数据库表列表成功",
  "success": true
}
```

#### 3. 对象存储浏览

##### 获取桶列表

```http
GET /api/v1/browse/object_storage/{datasource_id}/buckets
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "data": [
    {
      "name": "my-bucket",
      "creation_date": "2024-01-01T12:00:00Z",
      "region": "us-east-1"
    }
  ],
  "message": "获取桶列表成功",
  "success": true
}
```

##### 获取对象列表

```http
GET /api/v1/browse/object_storage/{datasource_id}/buckets/{bucket_name}/objects?prefix=folder/&delimiter=/
Authorization: Bearer {token}
```

**查询参数**:
- `prefix`: 对象前缀 (默认: "")
- `delimiter`: 分隔符 (默认: "/")

**响应示例**:
```json
{
  "data": [
    {
      "key": "folder/file.txt",
      "name": "file.txt",
      "size": 1024,
      "last_modified": "2024-01-01T12:00:00Z",
      "etag": "d41d8cd98f00b204e9800998ecf8427e",
      "storage_class": "STANDARD",
      "type": "file"
    },
    {
      "key": "folder/subfolder/",
      "name": "subfolder/",
      "size": 0,
      "type": "folder"
    }
  ],
  "message": "获取对象列表成功",
  "success": true
}
```

### 仪表盘统计

#### 获取系统统计

```http
GET /api/v1/dashboard/stats
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "data": {
    "datasource_count": 5,
    "active_datasource_count": 4,
    "connected_datasource_count": 3,
    "total_size": 10485760,
    "total_files": 1500,
    "total_records": 50000,
    "type_distribution": {
      "filesystem": 2,
      "database": 2,
      "object_storage": 1
    },
    "size_by_type": {
      "filesystem": 5242880,
      "database": 3145728,
      "object_storage": 2097152
    }
  },
  "message": "获取统计数据成功",
  "success": true
}
```

### 系统健康检查

```http
GET /api/v1/health
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "data": {
    "status": "healthy",
    "timestamp": "2024-01-01T12:00:00Z",
    "uptime": 3600.5,
    "version": "1.0.0",
    "services": {
      "database": {
        "status": "healthy",
        "connection": true
      },
      "redis": {
        "status": "healthy",
        "enabled": false,
        "connection": true
      },
      "system": {
        "cpu_percent": 25.5,
        "memory_percent": 65.2,
        "disk_percent": 80.1,
        "available_memory_mb": 2048
      }
    }
  },
  "message": "系统健康检查成功",
  "success": true
}
```

## 📋 数据源类型配置

### 文件系统 (filesystem)

```json
{
  "type": "filesystem",
  "name": "local_files",
  "cname": "本地文件系统",
  "desc": "本地文件系统数据源",
  "config": {
    "path": "/data/files",
    "encoding": "utf-8",
    "extensions": [".txt", ".csv", ".json", ".xlsx"]
  }
}
```

### 数据库 (database)

```json
{
  "type": "database",
  "name": "mysql_db",
  "cname": "MySQL数据库",
  "desc": "生产环境MySQL数据库",
  "config": {
    "db_type": "MySQL",
    "host": "localhost",
    "port": 3306,
    "database": "production_db",
    "user": "username",
    "password": "password"
  }
}
```

### 对象存储 (object_storage)

```json
{
  "type": "object_storage", 
  "name": "s3_storage",
  "cname": "S3对象存储",
  "desc": "AWS S3对象存储",
  "config": {
    "bucket": "my-bucket",
    "endpoint": "https://s3.amazonaws.com",
    "access_key": "ACCESS_KEY",
    "secret_key": "SECRET_KEY",
    "region": "us-east-1",
    "ssl": true
  }
}
```

## 🚨 错误处理

### HTTP状态码

- `200`: 请求成功
- `201`: 资源创建成功
- `400`: 请求参数错误
- `401`: 未授权或token无效
- `403`: 权限不足
- `404`: 资源不存在
- `409`: 资源冲突
- `422`: 请求数据验证失败
- `500`: 服务器内部错误

### 错误响应格式

```json
{
  "detail": "错误描述信息",
  "success": false,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 📈 最佳实践

### 1. 连接管理

- 使用连接池管理HTTP连接
- 设置合理的超时时间 (建议30秒)
- 实现重试机制处理临时网络问题

### 2. 认证管理

- 安全存储访问令牌
- 实现自动token刷新机制
- 处理token过期情况

### 3. 错误处理

- 实现统一的错误处理机制
- 记录详细的API调用日志
- 对不同类型的错误进行分类处理

### 4. 性能优化

- 使用分页查询大量数据
- 实现客户端缓存机制
- 并发请求时注意API限流

### 5. 安全考虑

- 使用HTTPS连接 (生产环境)
- 不在客户端存储敏感配置信息
- 实现适当的访问日志记录

## 🔧 故障排查

### 常见问题

1. **连接失败**
   - 检查API服务是否正常运行
   - 确认网络连接和防火墙设置
   - 验证API基础地址是否正确

2. **认证失败**
   - 检查用户名密码是否正确
   - 确认用户账户是否激活
   - 验证token是否过期

3. **权限不足**
   - 确认用户角色权限
   - 检查数据源访问权限设置

4. **数据获取失败**
   - 验证数据源配置是否正确
   - 检查数据源连接状态
   - 确认请求参数格式

### 调试建议

- 启用详细的HTTP请求/响应日志
- 使用API文档页面进行接口测试
- 检查系统健康状态接口
- 查看服务器端日志信息

## 📞 技术支持

如有问题或需要技术支持，请：

1. 查看API文档: http://localhost:8000/api/docs
2. 检查系统健康状态: `GET /api/v1/health`
3. 查看服务器日志获取详细错误信息
4. 联系系统管理员或开发团队
