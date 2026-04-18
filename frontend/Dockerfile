# 构建阶段
FROM node:20-alpine AS builder

# 设置工作目录
WORKDIR /app

# 设置淘宝 npm 镜像源加速安装
RUN npm config set registry https://registry.npmmirror.com

# 复制 package.json 和 lock 文件
COPY package*.json ./

# 安装依赖
RUN npm install && npm install terser

# 复制源代码
COPY . .

# 构建生产版本（跳过类型检查，直接使用 vite 构建）
RUN npx vite build

# 生产阶段 - 使用 nginx 提供服务
FROM nginx:alpine

# 复制构建产物到 nginx 目录
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

# 启动 nginx
CMD ["nginx", "-g", "daemon off;"]
