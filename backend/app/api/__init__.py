from fastapi import APIRouter

from app.api.endpoints import (
    auth,
    users,
    datasources,
    browse,
    health,
    dashboard,
    sso,
    system_status,
    datasource_all_data,
    roles,
    analyze,
    code_execute,
)

# 创建API路由器
api_router = APIRouter()

# 包含各个模块的路由
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(sso.router, prefix="/sso", tags=["sso"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(datasources.router, prefix="/datasources", tags=["datasources"])
api_router.include_router(browse.router, prefix="/browse", tags=["browse"])
api_router.include_router(datasource_all_data.router, prefix="/browse_all_data", tags=["browse_all_data"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(system_status.router, prefix="/system", tags=["system"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
api_router.include_router(analyze.router, prefix="/analyze", tags=["analyze"])
api_router.include_router(code_execute.router, prefix="/code", tags=["code_execute"])
