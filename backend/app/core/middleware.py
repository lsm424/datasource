import time
import uuid
from typing import Callable
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response as StarletteResponse

from app.core.config import settings


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.time()
        
        # 生成请求ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # 记录请求信息
        client_ip = self.get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        print(f"[{request_id}] {request.method} {request.url.path} - IP: {client_ip}")
        
        response = await call_next(request)
        
        # 计算处理时间
        process_time = time.time() - start_time
        
        # 添加响应头
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        # 记录响应信息
        print(f"[{request_id}] Response: {response.status_code} - Time: {process_time:.3f}s")
        
        return response
    
    def get_client_ip(self, request: Request) -> str:
        """获取客户端真实IP"""
        # 检查代理头
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全响应头中间件"""
    
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        
        # 添加安全相关的响应头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # 在HTTPS环境下添加HSTS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        
        # CSP策略（根据需要调整）
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-eval' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' ws: wss:;"
        )
        response.headers["Content-Security-Policy"] = csp_policy
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """简单的速率限制中间件"""
    
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients = {}
    
    async def dispatch(
        self,
        request: Request, 
        call_next: RequestResponseEndpoint
    ) -> StarletteResponse:
        client_ip = self.get_client_ip(request)
        current_time = time.time()
        
        # 清理过期记录
        self.cleanup_expired_records(current_time)
        
        # 检查速率限制
        if client_ip in self.clients:
            client_data = self.clients[client_ip]
            if len(client_data["requests"]) >= self.calls:
                # 达到速率限制
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="请求过于频繁，请稍后再试"
                )
            
            client_data["requests"].append(current_time)
        else:
            self.clients[client_ip] = {"requests": [current_time]}
        
        response = await call_next(request)
        return response
    
    def get_client_ip(self, request: Request) -> str:
        """获取客户端IP"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0]
        return request.client.host if request.client else "unknown"
    
    def cleanup_expired_records(self, current_time: float):
        """清理过期记录"""
        for client_ip in list(self.clients.keys()):
            requests = self.clients[client_ip]["requests"]
            # 只保留在时间窗口内的请求
            valid_requests = [
                req_time for req_time in requests
                if current_time - req_time <= self.period
            ]
            
            if valid_requests:
                self.clients[client_ip]["requests"] = valid_requests
            else:
                del self.clients[client_ip]


def setup_middleware(app: FastAPI):
    """设置所有中间件"""
    
    # 请求日志中间件
    if settings.ACCESS_LOG:
        app.add_middleware(RequestLoggingMiddleware)
    
    # 安全头中间件
    app.add_middleware(SecurityHeadersMiddleware)
    
    # 速率限制中间件（仅在生产环境启用）
    if settings.ENVIRONMENT == "production":
        app.add_middleware(RateLimitMiddleware, calls=100, period=60)
