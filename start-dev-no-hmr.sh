#!/bin/bash

# 启动开发服务器（无HMR版本）
# 这个脚本使用生产构建模式来避免HMR问题

echo "🚀 启动数据浏览器（无HMR模式）..."

# 检查是否在正确的目录
if [ ! -f "package.json" ]; then
    echo "❌ 请在项目根目录运行此脚本"
    exit 1
fi

# 构建前端
echo "📦 构建前端..."
npm run build

# 启动后端
echo "🔧 启动后端服务器..."
cd backend
python main.py &
BACKEND_PID=$!
cd ..

# 等待后端启动
sleep 3

# 启动前端预览服务器
echo "🌐 启动前端预览服务器..."
npm run preview &
FRONTEND_PID=$!

# 保存PID
echo $BACKEND_PID > .backend_pid
echo $FRONTEND_PID > .frontend_pid

echo "✅ 服务器启动成功！"
echo "🌐 前端地址: http://localhost:4173"
echo "🔧 后端地址: http://localhost:8000"
echo "📚 API文档: http://localhost:8000/api/docs"
echo "⚠️  注意：代码修改后需要重新运行此脚本"

# 等待中断信号
trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; rm -f .backend_pid .frontend_pid; exit' INT
wait


