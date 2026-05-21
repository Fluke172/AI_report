#!/bin/bash
# 服务器端部署脚本 - 放在 /opt/ai-report/deploy.sh
set -e
cd /opt/ai-report

echo ">>> 拉取最新代码..."
git pull origin main

echo ">>> 重新构建并启动..."
docker compose up -d --build

echo ">>> 等待服务就绪..."
sleep 3

echo ">>> 健康检查..."
if curl -sf http://localhost:8000/health > /dev/null; then
    echo "✅ 部署成功！"
else
    echo "❌ 健康检查失败，回滚..."
    git checkout HEAD~1
    docker compose up -d --build
    echo "已回滚到上一版本"
    exit 1
fi
