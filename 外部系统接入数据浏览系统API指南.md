# 外部系统接入数据浏览系统API指南

## 📌 概述

本指南为外部系统提供完整的API接入方案，支持通过RESTful API访问数据浏览系统的所有功能，包括标准API调用和单点登录(SSO)集成。

## 🌐 基础信息

- **API基础地址**: `http://localhost:8000/api/v1`
- **认证方式**: JWT Bearer Token / API Key / SSO Token
- **数据格式**: JSON
- **字符编码**: UTF-8

## 📚 API文档

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## 🔐 认证方式

### 方式1：标准JWT认证

#### 用户登录
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
    "user": {
      "id": "user_id",
      "username": "username",
      "role": "admin"
    }
  }
}
```

#### 使用Token
在所有后续请求中添加Authorization头：
```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

### 方式2：SSO单点登录 ⭐ **推荐**

#### JWT Token共享方案

外部系统与数据浏览系统共享相同的JWT密钥和token格式。

**配置环境变量**:
```bash
ENABLE_SSO=true
SSO_SHARED_SECRET=your-shared-secret-key-with-external-system
```

**外部系统JWT Token格式**:
```json
{
  "sub": "user_12345",
  "username": "johndoe",
  "role": "admin",
  "email": "john@example.com",
  "name": "John Doe",
  "system": "external_system_a",
  "exp": 1640995200,
  "iat": 1640908800,
  "type": "access"
}
```

**外部系统生成Token示例 (Python)**:
```python
import jwt
from datetime import datetime, timedelta

def generate_compatible_token(user_data):
    payload = {
        "sub": user_data["user_id"],
        "username": user_data["username"],
        "role": user_data.get("role", "user"),
        "email": user_data.get("email"),
        "name": user_data.get("name"),
        "system": "your_system_name",
        "exp": datetime.utcnow() + timedelta(minutes=30),
        "iat": datetime.utcnow(),
        "type": "access"
    }
    return jwt.encode(payload, "your-shared-secret", algorithm="HS256")

# 使用生成的token直接访问数据浏览系统API
token = generate_compatible_token(user_info)
headers = {"Authorization": f"Bearer {token}"}
response = requests.get("http://localhost:8000/api/v1/datasources", headers=headers)
```

#### Token交换方案

```bash
# 将外部token转换为本系统token
curl -X POST http://localhost:8000/api/v1/sso/token-exchange \
     -H "Content-Type: application/json" \
     -d '{
       "external_token": "<external_system_token>",
       "system_name": "system_a"
     }'
```

#### API Key方案

```bash
# 生成API Key (管理员权限)
curl -X POST http://localhost:8000/api/v1/sso/generate-api-key \
     -H "Authorization: Bearer <admin_token>" \
     -H "Content-Type: application/json" \
     -d '{
       "target_user_id": "user_123",
       "system_name": "external_system"
     }'

# 使用API Key访问
curl -H "Authorization: Bearer <api_key>" \
     http://localhost:8000/api/v1/datasources
```

## 📊 核心API接口

### 数据源管理

#### 1. 获取数据源列表
```http
GET /api/v1/datasources?page=1&limit=20&type=filesystem&is_active=true&search=keyword
Authorization: Bearer <token>
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
  "success": true
}
```

#### 2. 获取数据源详情
```http
GET /api/v1/datasources/{datasource_id}
Authorization: Bearer <token>
```

#### 3. 获取数据源统计
```http
GET /api/v1/datasources/statistics
Authorization: Bearer <token>
```

### 数据浏览

#### 1. 文件系统浏览
```http
GET /api/v1/browse/filesystem/{datasource_id}/files?path=/data/folder
Authorization: Bearer <token>
```

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
    }
  ],
  "success": true
}
```

#### 2. 数据库表浏览
```http
GET /api/v1/browse/database/{datasource_id}/tables?database=test_db
Authorization: Bearer <token>
```

#### 3. 对象存储浏览
```http
# 获取桶列表
GET /api/v1/browse/object_storage/{datasource_id}/buckets
Authorization: Bearer <token>

# 获取对象列表
GET /api/v1/browse/object_storage/{datasource_id}/buckets/{bucket_name}/objects?prefix=folder/&delimiter=/
Authorization: Bearer <token>
```

### 仪表盘统计
```http
GET /api/v1/dashboard/stats
Authorization: Bearer <token>
```

### 系统健康检查
```http
GET /api/v1/health
Authorization: Bearer <token>
```

## 🔧 SSO相关接口

### 1. Token验证
```http
POST /api/v1/sso/validate-shared-token
Content-Type: application/json

{
  "shared_token": "your_jwt_token"
}
```

### 2. 获取SSO用户信息
```http
GET /api/v1/sso/me/mixed
Authorization: Bearer <token>
```

### 3. 系统集成测试
```http
POST /api/v1/sso/test-integration
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "test_token": "test_jwt_token",
  "auth_type": "shared_jwt",
  "system_name": "test_system"
}
```

## 💻 客户端集成示例

### Python客户端示例

```python
import requests
import jwt
from datetime import datetime, timedelta

class DataBrowserClient:
    def __init__(self, base_url="http://localhost:8000/api/v1", 
                 shared_secret=None):
        self.base_url = base_url
        self.shared_secret = shared_secret
        self.token = None
        self.headers = {'Content-Type': 'application/json'}
    
    def login_standard(self, username, password):
        """标准登录"""
        response = requests.post(f"{self.base_url}/auth/login", json={
            "username": username,
            "password": password
        })
        
        if response.status_code == 200:
            result = response.json()
            self.token = result['data']['access_token']
            self.headers['Authorization'] = f"Bearer {self.token}"
            return result
        else:
            raise Exception(f"登录失败: {response.status_code}")
    
    def login_sso(self, user_data):
        """SSO登录 - JWT共享方式"""
        if not self.shared_secret:
            raise Exception("SSO登录需要配置共享密钥")
        
        payload = {
            "sub": user_data["user_id"],
            "username": user_data["username"],
            "role": user_data.get("role", "user"),
            "email": user_data.get("email"),
            "name": user_data.get("name"),
            "system": user_data.get("system", "external"),
            "exp": datetime.utcnow() + timedelta(minutes=30),
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        self.token = jwt.encode(payload, self.shared_secret, algorithm="HS256")
        self.headers['Authorization'] = f"Bearer {self.token}"
        return {"access_token": self.token}
    
    def get_datasources(self, **params):
        """获取数据源列表"""
        response = requests.get(f"{self.base_url}/datasources", 
                              headers=self.headers, params=params)
        return response.json()
    
    def get_datasource_detail(self, datasource_id):
        """获取数据源详情"""
        response = requests.get(f"{self.base_url}/datasources/{datasource_id}",
                              headers=self.headers)
        return response.json()
    
    def browse_filesystem(self, datasource_id, path="/"):
        """浏览文件系统"""
        response = requests.get(
            f"{self.base_url}/browse/filesystem/{datasource_id}/files",
            headers=self.headers, 
            params={"path": path}
        )
        return response.json()
    
    def browse_database_tables(self, datasource_id, database=None):
        """获取数据库表列表"""
        params = {"database": database} if database else {}
        response = requests.get(
            f"{self.base_url}/browse/database/{datasource_id}/tables",
            headers=self.headers, 
            params=params
        )
        return response.json()
    
    def browse_object_storage_buckets(self, datasource_id):
        """获取对象存储桶列表"""
        response = requests.get(
            f"{self.base_url}/browse/object_storage/{datasource_id}/buckets",
            headers=self.headers
        )
        return response.json()
    
    def get_dashboard_stats(self):
        """获取仪表盘统计"""
        response = requests.get(f"{self.base_url}/dashboard/stats",
                              headers=self.headers)
        return response.json()

# 使用示例
if __name__ == "__main__":
    # 创建客户端 - SSO方式
    client = DataBrowserClient(shared_secret="your-shared-secret")
    
    # SSO登录
    user_info = {
        "user_id": "external_user_123",
        "username": "john_doe",
        "email": "john@example.com",
        "name": "John Doe",
        "role": "admin",
        "system": "external_crm"
    }
    
    try:
        # 登录
        login_result = client.login_sso(user_info)
        print(f"SSO登录成功: {user_info['username']}")
        
        # 获取数据源列表
        datasources = client.get_datasources(limit=10)
        print(f"找到 {datasources['total']} 个数据源")
        
        # 浏览数据源
        for ds in datasources['data']:
            print(f"数据源: {ds['name']} ({ds['type']})")
            
            if ds['type'] == 'filesystem':
                files = client.browse_filesystem(ds['id'])
                print(f"  文件数: {len(files['data'])}")
            elif ds['type'] == 'database':
                tables = client.browse_database_tables(ds['id'])
                print(f"  表数: {len(tables.get('data', []))}")
            elif ds['type'] == 'object_storage':
                buckets = client.browse_object_storage_buckets(ds['id'])
                print(f"  桶数: {len(buckets.get('data', []))}")
        
        # 获取统计信息
        stats = client.get_dashboard_stats()
        print(f"系统统计: {stats['data']['datasource_count']} 个数据源")
        
    except Exception as e:
        print(f"操作失败: {e}")
```

### Node.js客户端示例

```javascript
const axios = require('axios');
const jwt = require('jsonwebtoken');

class DataBrowserClient {
  constructor(baseUrl = 'http://localhost:8000/api/v1', sharedSecret = null) {
    this.baseUrl = baseUrl;
    this.sharedSecret = sharedSecret;
    this.token = null;
    
    this.client = axios.create({
      baseURL: this.baseUrl,
      timeout: 30000,
      headers: { 'Content-Type': 'application/json' }
    });
    
    // 请求拦截器
    this.client.interceptors.request.use(config => {
      if (this.token) {
        config.headers.Authorization = `Bearer ${this.token}`;
      }
      return config;
    });
  }

  async loginSSO(userData) {
    if (!this.sharedSecret) {
      throw new Error('SSO登录需要配置共享密钥');
    }

    const payload = {
      sub: userData.user_id,
      username: userData.username,
      role: userData.role || 'user',
      email: userData.email,
      name: userData.name,
      system: userData.system || 'external',
      exp: Math.floor(Date.now() / 1000) + (30 * 60),
      iat: Math.floor(Date.now() / 1000),
      type: 'access'
    };

    this.token = jwt.sign(payload, this.sharedSecret, { algorithm: 'HS256' });
    return { access_token: this.token };
  }

  async getDatasources(params = {}) {
    const response = await this.client.get('/datasources', { params });
    return response.data;
  }

  async browseFilesystem(datasourceId, path = '/') {
    const response = await this.client.get(
      `/browse/filesystem/${datasourceId}/files`,
      { params: { path } }
    );
    return response.data;
  }

  async getDashboardStats() {
    const response = await this.client.get('/dashboard/stats');
    return response.data;
  }
}

// 使用示例
async function main() {
  const client = new DataBrowserClient(
    'http://localhost:8000/api/v1', 
    'your-shared-secret'
  );
  
  try {
    // SSO登录
    await client.loginSSO({
      user_id: 'external_user_123',
      username: 'john_doe',
      email: 'john@example.com',
      name: 'John Doe',
      role: 'admin',
      system: 'external_crm'
    });
    
    console.log('SSO登录成功');
    
    // 获取数据源
    const datasources = await client.getDatasources({ limit: 10 });
    console.log(`找到 ${datasources.total} 个数据源`);
    
    // 获取统计
    const stats = await client.getDashboardStats();
    console.log(`系统统计: ${stats.data.datasource_count} 个数据源`);
    
  } catch (error) {
    console.error('操作失败:', error.message);
  }
}

main();
```

### Java客户端示例

```java
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.Date;
import java.util.HashMap;
import java.util.Map;

public class DataBrowserClient {
    private final String baseUrl;
    private final String sharedSecret;
    private final OkHttpClient httpClient;
    private final ObjectMapper objectMapper;
    private String token;
    
    public DataBrowserClient(String baseUrl, String sharedSecret) {
        this.baseUrl = baseUrl;
        this.sharedSecret = sharedSecret;
        this.httpClient = new OkHttpClient();
        this.objectMapper = new ObjectMapper();
    }
    
    public void loginSSO(Map<String, Object> userData) throws Exception {
        if (sharedSecret == null) {
            throw new Exception("SSO登录需要配置共享密钥");
        }
        
        long now = System.currentTimeMillis();
        Date expiryDate = new Date(now + 30 * 60 * 1000);
        
        Map<String, Object> claims = new HashMap<>();
        claims.put("sub", userData.get("user_id"));
        claims.put("username", userData.get("username"));
        claims.put("role", userData.getOrDefault("role", "user"));
        claims.put("email", userData.get("email"));
        claims.put("name", userData.get("name"));
        claims.put("system", userData.getOrDefault("system", "external"));
        claims.put("type", "access");
        
        this.token = Jwts.builder()
                .setClaims(claims)
                .setIssuedAt(new Date(now))
                .setExpiration(expiryDate)
                .signWith(SignatureAlgorithm.HS256, sharedSecret.getBytes())
                .compact();
    }
    
    public String getDatasources() throws Exception {
        Request request = new Request.Builder()
                .url(baseUrl + "/datasources")
                .addHeader("Authorization", "Bearer " + token)
                .build();
        
        try (Response response = httpClient.newCall(request).execute()) {
            return response.body().string();
        }
    }
    
    public static void main(String[] args) {
        try {
            DataBrowserClient client = new DataBrowserClient(
                "http://localhost:8000/api/v1", 
                "your-shared-secret"
            );
            
            Map<String, Object> userInfo = new HashMap<>();
            userInfo.put("user_id", "external_user_123");
            userInfo.put("username", "john_doe");
            userInfo.put("email", "john@example.com");
            userInfo.put("name", "John Doe");
            userInfo.put("role", "admin");
            userInfo.put("system", "external_crm");
            
            client.loginSSO(userInfo);
            System.out.println("SSO登录成功");
            
            String datasources = client.getDatasources();
            System.out.println("数据源列表: " + datasources);
            
        } catch (Exception e) {
            System.err.println("操作失败: " + e.getMessage());
        }
    }
}
```

## 🚀 快速开始

### 步骤1：启用SSO功能

在 `.env` 文件中添加：
```bash
ENABLE_SSO=true
SSO_SHARED_SECRET=your-shared-secret-key-must-match-external-system
SECRET_KEY=your-local-system-secret-key-min-32-chars
```

### 步骤2：数据库迁移

```bash
cd backend
python alembic/versions/add_sso_fields.py
```

### 步骤3：启动服务

```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 步骤4：验证集成

```bash
# 健康检查
curl http://localhost:8000/api/v1/health

# API文档
curl http://localhost:8000/api/docs

# SSO系统信息 (需要admin token)
curl -H "Authorization: Bearer <admin_token>" \
     http://localhost:8000/api/v1/sso/systems
```

## 📋 数据源类型配置

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

## 🚨 错误处理

### HTTP状态码
- `200`: 请求成功
- `201`: 资源创建成功
- `400`: 请求参数错误
- `401`: 未授权或token无效
- `403`: 权限不足
- `404`: 资源不存在
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

### 安全配置
- 使用强随机密钥（至少32字符）
- 生产环境启用HTTPS
- 定期轮换JWT密钥和API密钥
- 配置适当的CORS策略

### 性能优化
- 使用连接池管理HTTP连接
- 实现客户端缓存机制
- 使用分页查询大量数据
- 并发请求时注意API限流

### 错误处理
- 实现统一的错误处理机制
- 记录详细的API调用日志
- 实现重试机制处理临时网络问题
- 对不同类型的错误进行分类处理

## 🔧 故障排查

### 常见问题
1. **连接失败** → 检查API服务和网络连接
2. **认证失败** → 检查token格式和密钥配置
3. **权限不足** → 确认用户角色权限设置
4. **数据获取失败** → 验证数据源配置和连接状态

### 调试工具
```bash
# 查看API文档
curl http://localhost:8000/api/docs

# 健康检查
curl http://localhost:8000/api/v1/health

# 测试JWT token
curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/api/v1/datasources

# SSO集成测试
curl -X POST http://localhost:8000/api/v1/sso/test-integration \
     -H "Authorization: Bearer <admin_token>" \
     -d '{"test_token": "test_jwt", "auth_type": "shared_jwt"}'
```

## 📞 技术支持

如有问题或需要技术支持，请：

1. 查看API文档：http://localhost:8000/api/docs
2. 检查系统健康状态：`GET /api/v1/health`
3. 运行集成测试：`POST /api/v1/sso/test-integration`
4. 查看服务器日志获取详细错误信息
5. 联系系统管理员或开发团队

---

## 🎉 总结

通过本指南，您可以：

- ✅ **标准API接入** - 使用用户名密码获取JWT token访问API
- ✅ **单点登录集成** - 三种SSO方案满足不同安全需求
- ✅ **多语言支持** - Python、Node.js、Java客户端示例
- ✅ **完整数据访问** - 文件系统、数据库、对象存储全覆盖
- ✅ **生产环境就绪** - 安全配置和监控支持

无论您选择哪种接入方式，都能让外部系统用户便捷地访问数据浏览系统的强大功能！
