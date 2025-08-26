# JWT令牌过期处理修复

## 问题描述
用户反映当JWT令牌过期后，访问系统没有自动跳转回登录界面。

## 解决方案

### 1. 增强响应拦截器 (`src/utils/request.ts`)

**修复内容：**
- ✅ 在401错误处理中同时清除Pinia认证状态
- ✅ 避免重复跳转到登录页面
- ✅ 动态导入Auth Store避免循环依赖

```typescript
case 401:
  // 未认证，清除所有认证状态并跳转到登录页
  localStorage.removeItem('auth_token')
  
  // 清除Pinia认证状态
  const store = await getAuthStore()
  store.clearAuth()
  
  // 避免重复跳转到登录页
  if (router.currentRoute.value.path !== '/login') {
    router.push('/login')
    ElMessage.error('登录已过期，请重新登录')
  }
```

### 2. 增强Auth Store (`src/stores/auth.ts`)

**新增功能：**
- ✅ `validateToken()` - 主动验证token有效性
- ✅ `isTokenExpired()` - 检查token是否过期（基于时间戳）
- ✅ Token时间戳记录机制

**token过期检查：**
```typescript
const isTokenExpired = () => {
  const tokenTimestamp = localStorage.getItem('auth_token_timestamp')
  if (!tokenTimestamp) return true
  
  const tokenValidityPeriod = 60 * 60 * 1000 // 60分钟
  const tokenAge = Date.now() - parseInt(tokenTimestamp)
  return tokenAge > tokenValidityPeriod
}
```

**登录时保存时间戳：**
```typescript
localStorage.setItem('auth_token', loginData.token.access_token)
localStorage.setItem('auth_token_timestamp', Date.now().toString())
```

### 3. 增强路由守卫 (`src/router/index.ts`)

**新增检查：**
- ✅ 在路由守卫中额外检查token是否过期
- ✅ 发现过期token时立即清除认证状态

```typescript
// 额外检查：验证token有效性
if (authStore.token && authStore.isTokenExpired()) {
  console.log('⏰ Token已过期，重定向到登录页')
  authStore.clearAuth()
  next('/login')
  return
}
```

### 4. 主应用定时检查 (`src/main.ts`)

**定时检查机制：**
- ✅ 每5分钟检查一次token有效性
- ✅ 发现过期时自动跳转到登录页

```typescript
// 设置定期检查token有效性
setInterval(() => {
  if (authStore.isAuthenticated && authStore.isTokenExpired()) {
    console.log('⏰ 定时检查：Token已过期，清除认证状态')
    authStore.clearAuth()
    if (router.currentRoute.value.path !== '/login') {
      router.push('/login')
    }
  }
}, 5 * 60 * 1000) // 每5分钟检查一次
```

### 5. 初始化时过期检查

**启动时验证：**
- ✅ 应用启动时检查存储的token是否已过期
- ✅ 过期token会被立即清除

## 工作流程

### 场景1: API请求时token过期
1. 后端返回401错误
2. 响应拦截器捕获401
3. 清除localStorage和Pinia状态
4. 跳转到登录页面
5. 显示"登录已过期"提示

### 场景2: 页面路由切换时token过期  
1. 路由守卫检查认证状态
2. 发现token存在但已过期
3. 清除认证状态
4. 重定向到登录页面

### 场景3: 用户长时间停留在页面
1. 定时器每5分钟检查token
2. 发现token过期
3. 自动清除认证状态
4. 跳转到登录页面

### 场景4: 应用重新加载时token过期
1. 初始化认证状态时检查时间戳
2. 发现token已过期
3. 清除过期token
4. 用户需要重新登录

## 配置参数

- **Token有效期**: 60分钟（可在Auth Store中调整）
- **定时检查间隔**: 5分钟（可在main.ts中调整）
- **后端Token过期时间**: 30分钟（在后端配置中设置）

## 测试方法

### 手动测试token过期：
1. 登录系统
2. 在浏览器开发者工具中修改localStorage中的`auth_token_timestamp`为过期时间
3. 尝试访问任何需要认证的页面
4. 应该自动跳转到登录页面

### 后端401测试：
1. 登录系统
2. 在开发者工具中删除localStorage中的`auth_token`
3. 尝试访问API
4. 应该收到401错误并自动跳转到登录页面

## 日志输出

系统会输出以下调试日志：
- `🚫 检测到401错误，清除认证状态`
- `⏰ Token已过期，重定向到登录页`
- `⏰ 定时检查：Token已过期，清除认证状态`
- `✅ 已清除Pinia认证状态`

## 注意事项

1. **时间同步**: 确保客户端和服务器时间同步
2. **Token刷新**: 未来可以考虑实现自动token刷新机制
3. **多标签页**: 不同标签页的token状态会保持同步
4. **网络异常**: 网络异常不会触发token过期处理
