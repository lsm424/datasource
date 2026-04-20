# 应用镜像 Dockerfile
# 基于预构建的基础镜像，只包含应用代码
FROM data-browser-backend-base:latest
# docker build -f Dockerfile.base -t data-browser-backend-base:latest .

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p /app/data /app/logs /app/static

# 设置权限
RUN chmod +x /app/scripts/* 2>/dev/null || true

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# 启动命令
CMD ["python", "main.py"]
