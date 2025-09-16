from typing import List, Optional, Union
from pydantic import Field, validator
from pydantic_settings import BaseSettings
import os
from pathlib import Path

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    """应用配置"""
    
    # 基础配置
    PROJECT_NAME: str = "数据浏览系统"
    PROJECT_DESCRIPTION: str = "基于Web的多用户数据浏览系统"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    
    # 服务器配置
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    
    # 跨域配置
    ALLOWED_ORIGINS: Union[str, List[str]] = Field(
        default=["*"],  # 默认允许所有来源
        env="ALLOWED_ORIGINS"
    )
    
    # 数据库配置
    DATABASE_URL: str = Field(
        default="sqlite:///./data-browser.db", 
        env="DATABASE_URL",
        description="数据库连接字符串"
    )
    DATABASE_ECHO: bool = Field(default=False, env="DATABASE_ECHO")
    
    # Redis配置
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    REDIS_ENABLED: bool = Field(default=False, env="REDIS_ENABLED")
    
    # JWT配置
    SECRET_KEY: str = Field(
        default="your-secret-key-change-this-in-production",
        env="SECRET_KEY",
        min_length=32
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # 密码加密
    PWD_CONTEXT_SCHEMES: List[str] = ["bcrypt"]
    PWD_CONTEXT_DEPRECATED: str = "auto"
    
    # 文件上传配置
    UPLOAD_MAX_SIZE: int = Field(default=100 * 1024 * 1024, env="UPLOAD_MAX_SIZE")  # 100MB
    UPLOAD_ALLOWED_EXTENSIONS: Union[str, List[str]] = Field(
        default=[
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
            ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
            ".txt", ".csv", ".json", ".xml", ".yaml", ".yml",
            ".zip", ".rar", ".tar", ".gz"
        ],
        env="UPLOAD_ALLOWED_EXTENSIONS"
    )
    
    # 日志配置
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    ACCESS_LOG: bool = Field(default=True, env="ACCESS_LOG")
    LOG_FILE: Optional[str] = Field(default=None, env="LOG_FILE")
    
    # 数据源存储配置
    DATA_SOURCES_FILE: str = Field(
        default=str(PROJECT_ROOT / "data" / "datasources.json"),
        env="DATA_SOURCES_FILE"
    )
    
    # 缓存配置
    CACHE_EXPIRE_SECONDS: int = Field(default=300, env="CACHE_EXPIRE_SECONDS")  # 5分钟
    
    # 分页配置
    DEFAULT_PAGE_SIZE: int = Field(default=20, env="DEFAULT_PAGE_SIZE")
    MAX_PAGE_SIZE: int = Field(default=100, env="MAX_PAGE_SIZE")
    
    # 安全配置
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # 静态文件配置
    SERVE_STATIC_FILES: bool = Field(default=True, env="SERVE_STATIC_FILES")
    STATIC_FILES_DIRECTORY: str = Field(default="static", env="STATIC_FILES_DIRECTORY")
    
    # 邮件配置（可选）
    SMTP_TLS: bool = Field(default=True, env="SMTP_TLS")
    SMTP_PORT: Optional[int] = Field(default=587, env="SMTP_PORT")
    SMTP_HOST: Optional[str] = Field(default=None, env="SMTP_HOST")
    SMTP_USER: Optional[str] = Field(default=None, env="SMTP_USER")
    SMTP_PASSWORD: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    EMAILS_FROM_EMAIL: Optional[str] = Field(default=None, env="EMAILS_FROM_EMAIL")
    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = Field(default=24, env="EMAIL_RESET_TOKEN_EXPIRE_HOURS")
    
    # SSO单点登录配置
    ENABLE_SSO: bool = Field(default=False, env="ENABLE_SSO")
    
    # OAuth2/OIDC配置
    MICROSOFT_CLIENT_ID: Optional[str] = Field(default=None, env="MICROSOFT_CLIENT_ID")
    MICROSOFT_CLIENT_SECRET: Optional[str] = Field(default=None, env="MICROSOFT_CLIENT_SECRET")
    MICROSOFT_TENANT_ID: Optional[str] = Field(default="common", env="MICROSOFT_TENANT_ID")
    
    GOOGLE_CLIENT_ID: Optional[str] = Field(default=None, env="GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(default=None, env="GOOGLE_CLIENT_SECRET")
    
    # 外部系统集成配置
    EXTERNAL_SYSTEM_A_URL: Optional[str] = Field(default=None, env="EXTERNAL_SYSTEM_A_URL")
    EXTERNAL_SYSTEM_A_TOKEN: Optional[str] = Field(default=None, env="EXTERNAL_SYSTEM_A_TOKEN")
    
    EXTERNAL_SYSTEM_B_URL: Optional[str] = Field(default=None, env="EXTERNAL_SYSTEM_B_URL")
    EXTERNAL_SYSTEM_B_TOKEN: Optional[str] = Field(default=None, env="EXTERNAL_SYSTEM_B_TOKEN")
    
    # JWT共享密钥（与外部系统共享）
    SSO_SHARED_SECRET: Optional[str] = Field(default=None, env="SSO_SHARED_SECRET")
    
    # API Key配置
    API_KEY_ENABLED: bool = Field(default=True, env="API_KEY_ENABLED")
    API_KEY_EXPIRY_DAYS: int = Field(default=365, env="API_KEY_EXPIRY_DAYS")
    
    # 开发配置
    RELOAD: bool = Field(default=False, env="RELOAD")
    
    # 数据统计调度器配置
    ENABLE_SCHEDULER: bool = Field(default=True, env="ENABLE_SCHEDULER")
    STATS_CRON_HOUR: int = Field(default=2, env="STATS_CRON_HOUR")  # 每日统计时间（小时）
    STATS_CRON_MINUTE: int = Field(default=0, env="STATS_CRON_MINUTE")  # 每日统计时间（分钟）
    SCHEDULER_TIMEZONE: str = Field(default="Asia/Shanghai", env="SCHEDULER_TIMEZONE")
    
    @validator("ALLOWED_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v) -> List[str]:
        if isinstance(v, str) and v:
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        elif v is None or v == "":
            return ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]
        raise ValueError("ALLOWED_ORIGINS must be a string or list")
    
    @validator("UPLOAD_ALLOWED_EXTENSIONS", pre=True)
    def assemble_upload_extensions(cls, v) -> List[str]:
        if isinstance(v, str) and v:
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        elif v is None or v == "":
            return [".jpg", ".jpeg", ".png", ".gif", ".pdf", ".txt", ".csv", ".json", ".xml", ".zip"]
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# 创建全局配置实例
settings = Settings()

# 确保数据目录存在
data_dir = Path(settings.DATA_SOURCES_FILE).parent
data_dir.mkdir(exist_ok=True)
