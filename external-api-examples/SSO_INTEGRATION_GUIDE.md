# 数据浏览系统单点登录(SSO)集成指南

## 📌 概述

本指南详细介绍如何实现外部系统与数据浏览系统的单点登录集成，让用户在外部系统登录后能够直接访问数据浏览系统的API接口，无需重复认证。

## 🔐 SSO认证方案

### 方案一：JWT Token共享 ⭐ **推荐**

外部系统与数据浏览系统共享相同的JWT密钥和token格式，实现无缝认证。

**优点：**
- 实现简单，开发成本低
- 性能优秀，无需额外网络请求
- 支持离线验证

**配置步骤：**

1. **环境变量配置**
```bash
# 启用SSO功能
ENABLE_SSO=true

# 设置与外部系统共享的JWT密钥
SSO_SHARED_SECRET=your-shared-secret-key-with-external-system

# 标准JWT密钥（用于本系统用户）
SECRET_KEY=your-local-secret-key
```

2. **外部系统JWT Token格式**
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

3. **API调用示例**
```bash
# 使用外部系统生成的JWT Token直接访问数据浏览系统API
curl -H "Authorization: Bearer <external_jwt_token>" \
     http://localhost:8000/api/v1/datasources
```

### 方案二：外部Token验证

数据浏览系统调用外部系统的API来验证token有效性。

**优点：**
- 安全性高，token验证实时
- 支持复杂的权限控制
- 无需共享密钥

**配置步骤：**

1. **环境变量配置**
```bash
ENABLE_SSO=true
EXTERNAL_SYSTEM_A_URL=http://external-system-a.com/api/v1/auth/validate
EXTERNAL_SYSTEM_B_URL=http://external-system-b.com/api/v1/user/verify
```

2. **API调用示例**
```bash
# Token交换：将外部token转换为本系统token
curl -X POST http://localhost:8000/api/v1/sso/token-exchange \
     -H "Content-Type: application/json" \
     -d '{
       "external_token": "<external_system_token>",
       "system_name": "system_a"
     }'
```

### 方案三：API Key认证

为外部系统生成长期有效的API Key。

**优点：**
- 配置简单
- 适合系统间调用
- 支持权限隔离

**配置步骤：**

1. **生成API Key**
```bash
curl -X POST http://localhost:8000/api/v1/sso/generate-api-key \
     -H "Authorization: Bearer <admin_token>" \
     -H "Content-Type: application/json" \
     -d '{
       "target_user_id": "user_123",
       "system_name": "external_system"
     }'
```

2. **使用API Key**
```bash
curl -H "Authorization: Bearer <api_key>" \
     http://localhost:8000/api/v1/datasources
```

## 🚀 快速开始

### 步骤1：启用SSO功能

在数据浏览系统的 `.env` 文件中添加：

```bash
# 基础SSO配置
ENABLE_SSO=true
SSO_SHARED_SECRET=your-32-char-shared-secret-key
API_KEY_ENABLED=true
API_KEY_EXPIRY_DAYS=365

# 外部系统配置（可选）
EXTERNAL_SYSTEM_A_URL=http://your-external-system.com/api/auth/validate
```

### 步骤2：数据库迁移

如果使用数据库，需要更新用户表结构：

```sql
-- 添加SSO相关字段
ALTER TABLE users ADD COLUMN external_id VARCHAR(200) UNIQUE;
ALTER TABLE users ADD COLUMN extra_metadata JSON;
CREATE INDEX idx_users_external_id ON users(external_id);
```

### 步骤3：测试SSO集成

```bash
# 测试JWT共享认证
curl -X POST http://localhost:8000/api/v1/sso/test-integration \
     -H "Authorization: Bearer <admin_token>" \
     -H "Content-Type: application/json" \
     -d '{
       "test_token": "<your_test_jwt_token>",
       "auth_type": "shared_jwt",
       "system_name": "test_system"
     }'
```

## 💻 各语言集成示例

### Python集成示例

```python
import jwt
import requests
from datetime import datetime, timedelta

class DataBrowserSSOClient:
    def __init__(self, base_url="http://localhost:8000/api/v1", 
                 shared_secret="your-shared-secret"):
        self.base_url = base_url
        self.shared_secret = shared_secret
    
    def generate_shared_jwt(self, user_data):
        """生成与数据浏览系统兼容的JWT Token"""
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
        
        return jwt.encode(payload, self.shared_secret, algorithm="HS256")
    
    def access_data_browser_api(self, user_data, endpoint="/datasources"):
        """使用SSO访问数据浏览系统API"""
        token = self.generate_shared_jwt(user_data)
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{self.base_url}{endpoint}", headers=headers)
        
        return response.json()

# 使用示例
client = DataBrowserSSOClient()

# 用户在你的系统登录后
user_info = {
    "user_id": "12345",
    "username": "johndoe",
    "email": "john@example.com",
    "name": "John Doe",
    "role": "admin"
}

# 直接访问数据浏览系统API
result = client.access_data_browser_api(user_info)
print("数据源列表:", result)
```

### Node.js集成示例

```javascript
const jwt = require('jsonwebtoken');
const axios = require('axios');

class DataBrowserSSOClient {
  constructor(baseUrl = 'http://localhost:8000/api/v1', sharedSecret = 'your-shared-secret') {
    this.baseUrl = baseUrl;
    this.sharedSecret = sharedSecret;
  }

  generateSharedJWT(userData) {
    const payload = {
      sub: userData.user_id,
      username: userData.username,
      role: userData.role || 'user',
      email: userData.email,
      name: userData.name,
      system: 'your_system_name',
      exp: Math.floor(Date.now() / 1000) + (30 * 60), // 30 minutes
      iat: Math.floor(Date.now() / 1000),
      type: 'access'
    };

    return jwt.sign(payload, this.sharedSecret, { algorithm: 'HS256' });
  }

  async accessDataBrowserAPI(userData, endpoint = '/datasources') {
    const token = this.generateSharedJWT(userData);
    
    try {
      const response = await axios.get(`${this.baseUrl}${endpoint}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      return response.data;
    } catch (error) {
      throw new Error(`API调用失败: ${error.message}`);
    }
  }
}

// 使用示例
async function example() {
  const client = new DataBrowserSSOClient();
  
  const userInfo = {
    user_id: '12345',
    username: 'johndoe',
    email: 'john@example.com',
    name: 'John Doe',
    role: 'admin'
  };
  
  try {
    const result = await client.accessDataBrowserAPI(userInfo);
    console.log('数据源列表:', result);
  } catch (error) {
    console.error('错误:', error.message);
  }
}

example();
```

### Java集成示例

```java
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.Date;
import java.util.HashMap;
import java.util.Map;

public class DataBrowserSSOClient {
    private final String baseUrl;
    private final String sharedSecret;
    private final OkHttpClient httpClient;
    private final ObjectMapper objectMapper;
    
    public DataBrowserSSOClient(String baseUrl, String sharedSecret) {
        this.baseUrl = baseUrl;
        this.sharedSecret = sharedSecret;
        this.httpClient = new OkHttpClient();
        this.objectMapper = new ObjectMapper();
    }
    
    public String generateSharedJWT(Map<String, Object> userData) {
        long now = System.currentTimeMillis();
        Date expiryDate = new Date(now + 30 * 60 * 1000); // 30 minutes
        
        Map<String, Object> claims = new HashMap<>();
        claims.put("sub", userData.get("user_id"));
        claims.put("username", userData.get("username"));
        claims.put("role", userData.getOrDefault("role", "user"));
        claims.put("email", userData.get("email"));
        claims.put("name", userData.get("name"));
        claims.put("system", "your_system_name");
        claims.put("type", "access");
        
        return Jwts.builder()
                .setClaims(claims)
                .setIssuedAt(new Date(now))
                .setExpiration(expiryDate)
                .signWith(SignatureAlgorithm.HS256, sharedSecret.getBytes())
                .compact();
    }
    
    public String accessDataBrowserAPI(Map<String, Object> userData, String endpoint) throws Exception {
        String token = generateSharedJWT(userData);
        
        Request request = new Request.Builder()
                .url(baseUrl + endpoint)
                .addHeader("Authorization", "Bearer " + token)
                .build();
        
        try (Response response = httpClient.newCall(request).execute()) {
            if (response.isSuccessful()) {
                return response.body().string();
            } else {
                throw new Exception("API调用失败: " + response.code());
            }
        }
    }
    
    public static void main(String[] args) {
        try {
            DataBrowserSSOClient client = new DataBrowserSSOClient(
                "http://localhost:8000/api/v1", 
                "your-shared-secret"
            );
            
            Map<String, Object> userInfo = new HashMap<>();
            userInfo.put("user_id", "12345");
            userInfo.put("username", "johndoe");
            userInfo.put("email", "john@example.com");
            userInfo.put("name", "John Doe");
            userInfo.put("role", "admin");
            
            String result = client.accessDataBrowserAPI(userInfo, "/datasources");
            System.out.println("数据源列表: " + result);
            
        } catch (Exception e) {
            System.err.println("错误: " + e.getMessage());
        }
    }
}
```

## 🔧 高级配置

### 多系统JWT密钥管理

当需要支持多个外部系统时，可以为每个系统配置不同的密钥：

```python
# SSO配置类增强版
class MultiSystemSSOConfig:
    SYSTEM_SECRETS = {
        "system_a": "secret_key_for_system_a",
        "system_b": "secret_key_for_system_b",
        "system_c": "secret_key_for_system_c"
    }
    
    @classmethod
    def get_secret_by_system(cls, system_name: str) -> str:
        return cls.SYSTEM_SECRETS.get(system_name, settings.SSO_SHARED_SECRET)
```

### OAuth2/OIDC集成

对于更复杂的企业环境，支持标准OAuth2/OIDC协议：

```bash
# OAuth2配置
MICROSOFT_CLIENT_ID=your-microsoft-client-id
MICROSOFT_CLIENT_SECRET=your-microsoft-client-secret
MICROSOFT_TENANT_ID=your-tenant-id

GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### 用户权限映射

配置外部系统用户角色到本系统权限的映射：

```python
ROLE_MAPPING = {
    "system_a": {
        "superuser": "admin",
        "regular_user": "user",
        "viewer": "user"
    },
    "system_b": {
        "administrator": "admin",
        "member": "user"
    }
}
```

## 📊 监控和日志

### SSO认证日志

系统会记录所有SSO认证活动：

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "event": "sso_authentication",
  "user_id": "external_user_123",
  "system": "system_a",
  "method": "shared_jwt",
  "ip_address": "192.168.1.100",
  "success": true,
  "user_agent": "YourApp/1.0"
}
```

### API使用统计

监控各外部系统的API使用情况：

```bash
# 获取SSO使用统计
curl -H "Authorization: Bearer <admin_token>" \
     http://localhost:8000/api/v1/sso/usage-stats
```

## 🚨 安全注意事项

### 1. 密钥管理
- 使用强密钥（至少32字符）
- 定期轮换共享密钥
- 不同环境使用不同密钥

### 2. Token有效期
- 设置合理的token过期时间
- 实现token刷新机制
- 监控异常的token使用

### 3. 网络安全
- 生产环境使用HTTPS
- 配置适当的CORS策略
- 实现API限流和监控

### 4. 用户隐私
- 最小化传输用户信息
- 遵守数据保护法规
- 实现用户数据删除功能

## ❓ 故障排查

### 常见问题

1. **Token验证失败**
```bash
# 检查token格式和内容
python -c "import jwt; print(jwt.decode('your_token', options={'verify_signature': False}))"
```

2. **用户创建失败**
```bash
# 检查用户名冲突
curl -H "Authorization: Bearer <admin_token>" \
     http://localhost:8000/api/v1/users?search=username
```

3. **API Key过期**
```bash
# 验证API Key状态
curl -X POST http://localhost:8000/api/v1/sso/validate-api-key \
     -d '{"api_key": "your_api_key"}'
```

### 调试模式

启用详细的SSO调试日志：

```bash
LOG_LEVEL=DEBUG
ENABLE_SSO_DEBUG=true
```

## 📞 技术支持

如需技术支持，请：

1. 查看API文档：http://localhost:8000/api/docs
2. 测试SSO集成接口：`POST /api/v1/sso/test-integration`
3. 检查系统日志获取详细错误信息
4. 联系系统管理员或开发团队

---

通过以上配置，您的外部系统就可以无缝集成数据浏览系统的单点登录功能，用户只需在外部系统登录一次，即可直接访问数据浏览系统的所有API接口。
