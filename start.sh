#!/bin/bash

# 数据浏览系统启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_message() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查Python版本
check_python() {
    if ! command_exists python3; then
        print_message $RED "错误: Python 3 未安装"
        exit 1
    fi
    
    python_version=$(python3 --version | cut -d " " -f 2)
    required_version="3.8"
    
    if [[ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]]; then
        print_message $RED "错误: Python 版本需要 >= 3.8，当前版本: $python_version"
        exit 1
    fi
    
    print_message $GREEN "✓ Python $python_version"
}

# 检查Node.js版本
check_nodejs() {
    if ! command_exists node; then
        print_message $RED "错误: Node.js 未安装"
        exit 1
    fi
    
    node_version=$(node --version | cut -d "v" -f 2)
    required_version="16.0.0"
    
    if [[ "$(printf '%s\n' "$required_version" "$node_version" | sort -V | head -n1)" != "$required_version" ]]; then
        print_message $RED "错误: Node.js 版本需要 >= 16.0.0，当前版本: $node_version"
        exit 1
    fi
    
    print_message $GREEN "✓ Node.js v$node_version"
}

# 初始化后端
init_backend() {
    print_message $BLUE "正在初始化后端..."
    
    cd backend
    
    # 检查是否有虚拟环境
    if [ ! -d "venv" ]; then
        print_message $YELLOW "创建Python虚拟环境..."
        python3 -m venv venv
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 升级pip
    pip install --upgrade pip
    
    # 安装依赖
    print_message $YELLOW "安装Python依赖包..."
    pip install -r requirements.txt
    
    # 检查环境变量文件
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            print_message $YELLOW "复制环境变量配置文件..."
            cp .env.example .env
            print_message $YELLOW "请编辑 backend/.env 文件配置数据库等信息"
        else
            print_message $YELLOW "创建默认环境变量文件..."
            cat > .env << EOF
ENVIRONMENT=development
HOST=0.0.0.0
PORT=8000
DATABASE_URL=sqlite:///./data-browser.db
SECRET_KEY=your-very-secret-key-change-this-in-production-min-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
LOG_LEVEL=INFO
EOF
        fi
    fi
    
    # 创建数据目录
    mkdir -p data logs static
    
    # 初始化数据库
    print_message $YELLOW "初始化数据库..."
    python -c "
from app.core.database import create_tables
import asyncio
asyncio.run(create_tables())
print('数据库初始化完成')
"
    
    # 提示创建管理员用户
    print_message $GREEN "后端初始化完成！"
    print_message $YELLOW "是否要创建管理员用户？(y/N)"
    read -r create_admin
    if [ "$create_admin" = "y" ] || [ "$create_admin" = "Y" ]; then
        python init_admin.py
    fi
    
    cd ..
}

# 初始化前端
init_frontend() {
    print_message $BLUE "正在初始化前端..."
    
    # 检查包管理器
    if command_exists pnpm; then
        PKG_MANAGER="pnpm"
    elif command_exists yarn; then
        PKG_MANAGER="yarn"
    else
        PKG_MANAGER="npm"
    fi
    
    print_message $YELLOW "使用包管理器: $PKG_MANAGER"
    
    # 安装依赖
    print_message $YELLOW "安装前端依赖包..."
    $PKG_MANAGER install
    
    print_message $GREEN "前端初始化完成！"
}

# 启动开发服务器
start_dev_servers() {
    print_message $BLUE "启动开发服务器..."
    
    # 启动后端服务器（后台）
    print_message $YELLOW "启动后端服务器..."
    cd backend
    source venv/bin/activate
    python main.py &
    BACKEND_PID=$!
    cd ..
    
    # 等待后端启动
    sleep 3
    
    # 启动前端开发服务器
    print_message $YELLOW "启动前端开发服务器..."
    if command_exists pnpm; then
        pnpm dev &
    elif command_exists yarn; then
        yarn dev &
    else
        npm run dev &
    fi
    FRONTEND_PID=$!
    
    # 保存PID以便后续停止
    echo $BACKEND_PID > .backend_pid
    echo $FRONTEND_PID > .frontend_pid
    
    print_message $GREEN "🎉 开发服务器启动成功！"
    print_message $BLUE "前端地址: http://localhost:5173"
    print_message $BLUE "后端地址: http://localhost:8000"
    print_message $BLUE "API文档: http://localhost:8000/api/docs"
    print_message $YELLOW "按 Ctrl+C 停止服务器"
    
    # 等待中断信号
    trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; rm -f .backend_pid .frontend_pid; exit' INT
    wait
}

# 停止服务器
stop_servers() {
    if [ -f ".backend_pid" ]; then
        BACKEND_PID=$(cat .backend_pid)
        kill $BACKEND_PID 2>/dev/null && print_message $GREEN "后端服务器已停止"
        rm -f .backend_pid
    fi
    
    if [ -f ".frontend_pid" ]; then
        FRONTEND_PID=$(cat .frontend_pid)
        kill $FRONTEND_PID 2>/dev/null && print_message $GREEN "前端服务器已停止"
        rm -f .frontend_pid
    fi
}

# 显示帮助信息
show_help() {
    echo "数据浏览系统启动脚本"
    echo ""
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  init     初始化项目（安装依赖、创建数据库等）"
    echo "  dev      启动开发服务器"
    echo "  stop     停止开发服务器"
    echo "  clean    清理依赖和缓存"
    echo "  admin    创建管理员用户"
    echo "  help     显示此帮助信息"
    echo ""
}

# 清理项目
clean_project() {
    print_message $YELLOW "清理项目..."
    
    # 停止服务器
    stop_servers
    
    # 清理前端
    rm -rf node_modules
    rm -rf dist
    
    # 清理后端
    rm -rf backend/venv
    rm -rf backend/__pycache__
    rm -rf backend/app/__pycache__
    find backend -name "*.pyc" -delete
    
    print_message $GREEN "项目清理完成！"
}

# 主函数
main() {
    case "${1:-dev}" in
        "init")
            print_message $BLUE "=== 初始化数据浏览系统 ==="
            check_python
            check_nodejs
            init_backend
            init_frontend
            print_message $GREEN "🎉 项目初始化完成！"
            print_message $BLUE "运行 '$0 dev' 启动开发服务器"
            ;;
        "dev")
            if [ ! -d "backend/venv" ] || [ ! -d "node_modules" ]; then
                print_message $YELLOW "检测到项目未初始化，正在自动初始化..."
                main init
            fi
            start_dev_servers
            ;;
        "stop")
            stop_servers
            ;;
        "clean")
            clean_project
            ;;
        "admin")
            cd backend
            if [ -d "venv" ]; then
                source venv/bin/activate
                python init_admin.py
            else
                print_message $RED "后端环境未初始化，请先运行: $0 init"
            fi
            cd ..
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_message $RED "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
