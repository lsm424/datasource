from fastapi import APIRouter

from app.api.endpoints import auth, users, datasources, browse, health, dashboard, sso

# 创建API路由器
api_router = APIRouter()

# 包含各个模块的路由
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(sso.router, prefix="/sso", tags=["sso"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(datasources.router, prefix="/datasources", tags=["datasources"])
api_router.include_router(browse.router, prefix="/browse", tags=["browse"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
