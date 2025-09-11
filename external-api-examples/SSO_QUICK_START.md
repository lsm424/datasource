# 🚀 数据浏览系统SSO快速开始指南

## 📋 概述

本指南将帮助您在**5分钟内**完成数据浏览系统的单点登录(SSO)配置，实现外部系统用户无缝访问。

## 🔧 快速配置步骤

### 步骤1：复制配置文件

```bash
# 进入数据浏览系统目录
cd data-browser

# 复制SSO配置示例
cp external-api-examples/sso_config.example .env
```

### 步骤2：修改关键配置

编辑 `.env` 文件，至少修改以下配置：

```bash
# 启用SSO
ENABLE_SSO=true

# 设置与外部系统共享的JWT密钥（重要！）
SSO_SHARED_SECRET=your-shared-secret-key-must-match-external-system

# 本系统的密钥
SECRET_KEY=your-local-system-secret-key-min-32-chars
```

### 步骤3：启动服务

```bash
# 启动后端服务
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 验证服务启动
curl http://localhost:8000/api/v1/health
```

### 步骤4：运行演示测试

```bash
# 安装演示依赖
pip install PyJWT requests httpx

# 运行SSO演示
python external-api-examples/sso_demo.py
```

## 🎯 三种集成方式选择

### 方式1：JWT Token共享 ⭐ **最简单**

**适用场景**：外部系统和数据浏览系统可以共享JWT密钥

**配置要求**：
- 外部系统使用相同的JWT密钥签名token
- Token格式包含必要字段（sub, username, role等）

**外部系统代码示例**：
```python
import jwt
from datetime import datetime, timedelta

def generate_compatible_token(user_data):
    payload = {
        "sub": user_data["user_id"],
        "username": user_data["username"],
        "role": user_data["role"],
        "exp": datetime.utcnow() + timedelta(minutes=30),
        "type": "access"
    }
    return jwt.encode(payload, "your-shared-secret", algorithm="HS256")

# 使用生成的token直接访问数据浏览系统API
token = generate_compatible_token(user_info)
headers = {"Authorization": f"Bearer {token}"}
response = requests.get("http://localhost:8000/api/v1/datasources", headers=headers)
```

### 方式2：Token交换 🔄 **最安全**

**适用场景**：外部系统有自己的认证机制，需要token转换

**配置要求**：
- 配置外部系统验证端点
- 实现token交换逻辑

**外部系统代码示例**：
```python
# 第一步：将外部token换取本系统token
def exchange_token(external_token):
    response = requests.post("http://localhost:8000/api/v1/sso/token-exchange", json={
        "external_token": external_token,
        "system_name": "your_system"
    })
    return response.json()["data"]["access_token"]

# 第二步：使用换取的token访问API
local_token = exchange_token("your_external_token")
headers = {"Authorization": f"Bearer {local_token}"}
response = requests.get("http://localhost:8000/api/v1/datasources", headers=headers)
```

### 方式3：API Key ⚡ **最直接**

**适用场景**：系统间调用，不涉及最终用户

**配置要求**：
- 管理员权限生成API Key
- 长期有效，适合自动化系统

**外部系统代码示例**：
```python
# 管理员生成API Key（一次性操作）
admin_token = "admin_jwt_token"
response = requests.post("http://localhost:8000/api/v1/sso/generate-api-key", 
    headers={"Authorization": f"Bearer {admin_token}"},
    json={"target_user_id": "system_user", "system_name": "external_system"}
)
api_key = response.json()["data"]["api_key"]

# 长期使用API Key访问
headers = {"Authorization": f"Bearer {api_key}"}
response = requests.get("http://localhost:8000/api/v1/datasources", headers=headers)
```

## ✅ 验证集成成功

### 检查清单

- [ ] 服务启动正常：`http://localhost:8000/api/docs`
- [ ] SSO接口可访问：`GET /api/v1/sso/systems`
- [ ] 演示脚本运行成功
- [ ] 外部系统能正常获取数据源列表
- [ ] 用户信息正确映射

### 测试命令

```bash
# 1. 检查API文档
curl http://localhost:8000/api/docs

# 2. 健康检查
curl http://localhost:8000/api/v1/health

# 3. 测试JWT共享（替换your_jwt_token）
curl -H "Authorization: Bearer your_jwt_token" \
     http://localhost:8000/api/v1/datasources

# 4. 获取用户信息
curl -H "Authorization: Bearer your_jwt_token" \
     http://localhost:8000/api/v1/sso/me/mixed
```

## 🚨 生产环境配置

### 安全配置

```bash
# .env 生产环境配置
ENVIRONMENT=production
SECRET_KEY=your-very-strong-secret-key-at-least-32-characters-long
SSO_SHARED_SECRET=your-shared-secret-with-external-systems-32-chars

# 使用PostgreSQL
DATABASE_URL=postgresql://username:password@localhost:5432/databrowser

# 启用HTTPS（通过Nginx等反向代理）
ALLOWED_ORIGINS=https://your-domain.com,https://external-system.com
```

### Docker部署

```yaml
# docker-compose.yml 添加环境变量
version: '3.8'
services:
  backend:
    environment:
      - ENABLE_SSO=true
      - SSO_SHARED_SECRET=${SSO_SHARED_SECRET}
      - EXTERNAL_SYSTEM_A_URL=${EXTERNAL_SYSTEM_A_URL}
```

## 📞 故障排查

### 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| Token验证失败 | 密钥不匹配 | 确认SSO_SHARED_SECRET与外部系统一致 |
| 用户创建失败 | 用户名冲突 | 检查external_id字段，确保唯一性 |
| 权限不足 | 角色映射错误 | 检查token中的role字段 |
| 连接超时 | 外部系统不可达 | 检查EXTERNAL_SYSTEM_URL配置 |

### 调试模式

```bash
# 启用详细日志
LOG_LEVEL=DEBUG
SSO_DEBUG_ENABLED=true

# 查看日志
tail -f logs/app.log
```

## 📚 进阶功能

- **多租户支持**：不同外部系统使用不同配置
- **权限细粒度控制**：基于外部系统角色映射
- **OAuth2/OIDC**：企业级认证协议支持
- **审计日志**：完整的认证访问记录
- **监控告警**：异常访问模式检测

## 🆘 技术支持

- **API文档**：http://localhost:8000/api/docs
- **集成测试**：`POST /api/v1/sso/test-integration`
- **示例代码**：`external-api-examples/` 目录
- **配置模板**：`sso_config.example` 文件

---

🎉 **恭喜！** 您现在已经成功配置了数据浏览系统的单点登录功能。外部系统的用户现在可以无缝访问数据浏览系统的所有API接口！
