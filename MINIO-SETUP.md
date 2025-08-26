# MinIO 对象存储服务设置指南

## 概述

现在系统已经完全支持真实的MinIO对象存储服务，替换了之前的Mock数据。本指南将帮助您设置MinIO服务以便进行测试和生产使用。

## 快速启动（Docker方式）

### 1. 使用Docker运行MinIO

```bash
# 创建MinIO数据目录
mkdir -p ~/minio/data

# 启动MinIO服务器
docker run \
  -p 9000:9000 \
  -p 9001:9001 \
  --name minio \
  -v ~/minio/data:/data \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  quay.io/minio/minio server /data --console-address ":9001"
```

### 2. 访问MinIO控制台

- **API端点**: http://localhost:9000
- **Web控制台**: http://localhost:9001
- **用户名**: minioadmin
- **密码**: minioadmin

### 3. 创建测试存储桶

在MinIO控制台中创建一些测试存储桶：
- `test-bucket`
- `backup-bucket`
- `documents-bucket`

## 数据源配置

### 在系统中添加MinIO数据源

1. 登录数据浏览系统
2. 进入"数据源管理"
3. 点击"新增数据源"
4. 选择类型："对象存储"
5. 填写配置：

```json
{
  "endpoint": "localhost:9000",
  "access_key": "minioadmin",
  "secret_key": "minioadmin",
  "use_ssl": false,
  "region": "us-east-1"
}
```

## 生产环境配置

### 1. 安全配置

```json
{
  "endpoint": "your-minio-server.com:9000",
  "access_key": "your-access-key",
  "secret_key": "your-secret-key", 
  "use_ssl": true,
  "region": "us-east-1"
}
```

### 2. 集群部署

对于生产环境，建议使用MinIO集群部署：

```bash
# 4节点集群示例
docker run -d \
  --name minio-cluster \
  -p 9000:9000 \
  -p 9001:9001 \
  -v /data1:/data1 \
  -v /data2:/data2 \
  -v /data3:/data3 \
  -v /data4:/data4 \
  -e "MINIO_ROOT_USER=admin" \
  -e "MINIO_ROOT_PASSWORD=your-strong-password" \
  quay.io/minio/minio server \
  http://minio{1...4}/data{1...4} \
  --console-address ":9001"
```

## 功能特性

### 已支持的功能

✅ **存储桶管理**
- 列出所有存储桶
- 创建新存储桶  
- 删除存储桶

✅ **对象操作**
- 浏览对象列表
- 上传文件
- 下载文件
- 删除对象
- 获取对象信息

✅ **高级功能**
- 前缀过滤
- 分页浏览
- 连接测试
- 错误处理

### API端点

系统提供以下MinIO相关的API端点：

```
GET    /api/v1/browse/object_storage/{id}/buckets                    # 获取存储桶列表
POST   /api/v1/browse/object_storage/{id}/buckets                    # 创建存储桶
DELETE /api/v1/browse/object_storage/{id}/buckets/{bucket}           # 删除存储桶

GET    /api/v1/browse/object_storage/{id}/buckets/{bucket}/objects   # 获取对象列表
POST   /api/v1/browse/object_storage/{id}/buckets/{bucket}/objects   # 上传对象
GET    /api/v1/browse/object_storage/{id}/buckets/{bucket}/objects/{object}      # 下载对象
DELETE /api/v1/browse/object_storage/{id}/buckets/{bucket}/objects/{object}     # 删除对象
GET    /api/v1/browse/object_storage/{id}/buckets/{bucket}/objects/{object}/info # 获取对象信息

POST   /api/v1/browse/object_storage/{id}/test                       # 测试连接
```

## 测试连接

### 使用测试脚本

```bash
cd backend
python test_minio.py
```

### 预期输出

```
🧪 MinIO连接测试开始...
==================================================
✅ 连接成功!
📝 消息: MinIO连接成功
🏪 存储桶数量: 3
📂 测试列出存储桶...
✅ 找到 3 个存储桶:
   - test-bucket (region: us-east-1) created: 2024-01-20T10:30:00Z
   - backup-bucket (region: us-east-1) created: 2024-01-20T10:31:00Z
   - documents-bucket (region: us-east-1) created: 2024-01-20T10:32:00Z
==================================================
```

## 故障排除

### 常见问题

1. **连接被拒绝**
   - 确保MinIO服务器正在运行
   - 检查端口9000是否开放
   - 验证endpoint配置

2. **认证失败**
   - 检查access_key和secret_key
   - 确保MinIO用户有足够权限

3. **SSL错误**
   - 生产环境设置use_ssl: true
   - 开发环境可使用use_ssl: false

### 日志查看

MinIO服务器日志：
```bash
docker logs minio
```

系统后端日志：
```bash
# 查看FastAPI日志中的MinIO相关信息
tail -f backend/logs/app.log | grep -i minio
```

## 性能优化

### 1. 连接池配置

MinIO客户端会自动管理连接池，无需额外配置。

### 2. 批量操作

对于大量文件操作，考虑使用异步处理：

```python
# 示例：批量上传
async def batch_upload(files):
    tasks = []
    for file in files:
        task = upload_object_async(file)
        tasks.append(task)
    await asyncio.gather(*tasks)
```

### 3. 缓存策略

对于频繁访问的bucket列表，可以实现缓存：

```python
# Redis缓存示例
@cache(expire=300)  # 5分钟缓存
def get_cached_buckets(datasource_id):
    return minio_service.list_buckets()
```

---

**🎉 MinIO集成完成！**

现在您的数据浏览系统已经完全支持真实的MinIO对象存储服务，可以替代之前的Mock数据，提供完整的对象存储管理功能。
