#!/bin/bash

# 数据浏览器系统启动脚本
# 功能：构建镜像、停止旧容器、启动新容器

set -e

# 禁用 Git Bash 的路径转换（Windows 环境）
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL="*"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 容器和镜像名称
BACKEND_IMAGE="data-browser-backend"
FRONTEND_IMAGE="data-browser-frontend"
BACKEND_CONTAINER="data-browser-backend"
FRONTEND_CONTAINER="data-browser-frontend"
NETWORK_NAME="data-browser-network"

# 端口配置
BACKEND_PORT=8000
FRONTEND_PORT=5173

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}  数据浏览器系统 Docker 启动脚本${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# 获取脚本所在目录的绝对路径（兼容 Windows Git Bash）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 如果是 Windows 环境，转换为 Windows 路径格式
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    SCRIPT_DIR=$(cygpath -w "$SCRIPT_DIR")
fi
cd "$(dirname "${BASH_SOURCE[0]}")"

# 函数：检查并停止运行的容器
stop_running_containers() {
    echo -e "${YELLOW}[1/6] 检查并停止运行的容器...${NC}"
    
    # 停止后端容器
    if docker ps -q -f name="$BACKEND_CONTAINER" | grep -q .; then
        echo -e "  发现运行的后端容器，正在停止..."
        docker stop "$BACKEND_CONTAINER" >/dev/null 2>&1 || true
        docker rm "$BACKEND_CONTAINER" >/dev/null 2>&1 || true
        echo -e "  ${GREEN}✓ 后端容器已停止${NC}"
    else
        echo -e "  后端容器未运行"
    fi
    
    # 停止前端容器
    if docker ps -q -f name="$FRONTEND_CONTAINER" | grep -q .; then
        echo -e "  发现运行的前端容器，正在停止..."
        docker stop "$FRONTEND_CONTAINER" >/dev/null 2>&1 || true
        docker rm "$FRONTEND_CONTAINER" >/dev/null 2>&1 || true
        echo -e "  ${GREEN}✓ 前端容器已停止${NC}"
    else
        echo -e "  前端容器未运行"
    fi
    
    # 清理已停止的同名容器
    docker container prune -f >/dev/null 2>&1 || true
    echo ""
}

# 函数：创建 Docker 网络
create_network() {
    echo -e "${YELLOW}[2/6] 检查 Docker 网络...${NC}"
    if ! docker network ls | grep -q "$NETWORK_NAME"; then
        docker network create "$NETWORK_NAME" >/dev/null 2>&1
        echo -e "  ${GREEN}✓ 创建网络: $NETWORK_NAME${NC}"
    else
        echo -e "  网络已存在: $NETWORK_NAME"
    fi
    echo ""
}

# 函数：构建后端镜像
build_backend() {
    echo -e "${YELLOW}[3/6] 构建后端镜像...${NC}"
    cd "$SCRIPT_DIR/backend"
    
    if [ -f "Dockerfile" ]; then
        docker build -t "$BACKEND_IMAGE:latest" . --no-cache
        echo -e "  ${GREEN}✓ 后端镜像构建完成${NC}"
    else
        echo -e "  ${RED}✗ 后端 Dockerfile 不存在${NC}"
        exit 1
    fi
    echo ""
}

# 函数：构建前端镜像
build_frontend() {
    echo -e "${YELLOW}[4/6] 构建前端镜像...${NC}"
    cd "$SCRIPT_DIR/frontend"
    
    if [ -f "Dockerfile" ]; then
        docker build -t "$FRONTEND_IMAGE:latest" . --no-cache
        echo -e "  ${GREEN}✓ 前端镜像构建完成${NC}"
    else
        echo -e "  ${RED}✗ 前端 Dockerfile 不存在${NC}"
        exit 1
    fi
    echo ""
}

# 函数：启动后端容器
start_backend() {
    echo -e "${YELLOW}[5/6] 启动后端容器...${NC}"
    
    # 创建数据目录
    mkdir -p "$SCRIPT_DIR/backend/data"
    mkdir -p "$SCRIPT_DIR/backend/logs"
    mkdir -p "$SCRIPT_DIR/backend/static"
    
    docker run -d \
        --name "$BACKEND_CONTAINER" \
        --network "$NETWORK_NAME" \
        -p "$BACKEND_PORT:8000" \
        -v "$SCRIPT_DIR/backend/data:/app/data" \
        -v "$SCRIPT_DIR/backend/logs:/app/logs" \
        -v "$SCRIPT_DIR/backend/static:/app/static" \
        -e STATIC_FILES_DIRECTORY=/app/static \
        -e DATABASE_URL=sqlite:///./data/data-browser.db \
        --restart unless-stopped \
        "$BACKEND_IMAGE:latest"
    
    echo -e "  ${GREEN}✓ 后端容器已启动${NC}"
    echo -e "  后端地址: http://localhost:$BACKEND_PORT"
    echo ""
}

# 函数：启动前端容器
start_frontend() {
    echo -e "${YELLOW}[6/6] 启动前端容器...${NC}"
    
    # 等待后端服务就绪，确保 DNS 能解析
    echo -e "  等待后端服务就绪..."
    sleep 3
    
    docker run -d \
        --name "$FRONTEND_CONTAINER" \
        --network "$NETWORK_NAME" \
        -p "$FRONTEND_PORT:80" \
        --restart unless-stopped \
        "$FRONTEND_IMAGE:latest"
    
    echo -e "  ${GREEN}✓ 前端容器已启动${NC}"
    echo -e "  前端地址: http://localhost:$FRONTEND_PORT"
    echo ""
}

# 函数：等待服务就绪
wait_for_services() {
    echo -e "${YELLOW}等待服务就绪...${NC}"
    
    # 等待后端健康检查
    echo -n "  检查后端服务"
    for i in {1..30}; do
        if curl -sf http://localhost:$BACKEND_PORT/api/v1/health >/dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            break
        fi
        echo -n "."
        sleep 1
    done
    
    echo ""
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN}  系统启动完成！${NC}"
    echo -e "${GREEN}================================${NC}"
    echo ""
    echo -e "访问地址:"
    echo -e "  前端: ${BLUE}http://localhost${NC}"
    echo -e "  后端 API: ${BLUE}http://localhost:$BACKEND_PORT${NC}"
    echo ""
    echo -e "查看日志:"
    echo -e "  后端: docker logs -f $BACKEND_CONTAINER"
    echo -e "  前端: docker logs -f $FRONTEND_CONTAINER"
    echo ""
}

# 主执行流程
main() {
    # 检查 Docker 是否安装
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}错误: Docker 未安装${NC}"
        exit 1
    fi
    
    # 检查 Docker 是否运行
    if ! docker info >/dev/null 2>&1; then
        echo -e "${RED}错误: Docker 服务未运行${NC}"
        exit 1
    fi
    
    create_network
    build_backend
    build_frontend
    stop_running_containers
    start_backend
    start_frontend
    wait_for_services
}

# 执行主函数
main
