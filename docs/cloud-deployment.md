# AI 学习周报服务 - 云服务器部署流程

## 一、前置准备

### 1.1 服务器要求

| 项目 | 最低要求 | 建议配置 |
|------|---------|---------|
| 系统 | Ubuntu 20.04+ / CentOS 7+ | Ubuntu 22.04 LTS |
| CPU | 1 核 | 2 核 |
| 内存 | 1 GB | 2 GB |
| 磁盘 | 10 GB | 20 GB |
| 带宽 | 1 Mbps | 5 Mbps |
| 网络 | 可访问 ark.cn-beijing.volces.com | - |

### 1.2 需要的账号和凭证

- [ ] 云服务器 SSH 登录信息
- [ ] 火山方舟 API Key
- [ ] 火山方舟 Endpoint ID（doubao-lite-32k 接入点）
- [ ] 域名（可选，如需 HTTPS）

---

## 二、服务器初始化

### 2.1 安装 Docker

```bash
# Ubuntu
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl start docker
sudo systemctl enable docker

# 添加当前用户到 docker 组（免 sudo）
sudo usermod -aG docker $USER
newgrp docker
```

### 2.2 验证 Docker

```bash
docker --version
docker compose version
```

---

## 三、部署服务

### 3.1 上传代码

**方式A：Git（推荐）**
```bash
cd /opt
git clone <你的仓库地址> ai-report
cd ai-report
```

**方式B：SCP 上传**
```bash
# 本地执行
scp -r D:\Ai_Report user@服务器IP:/opt/ai-report

# 服务器执行
ssh user@服务器IP
cd /opt/ai-report
```

### 3.2 配置环境变量

```bash
cp .env.example .env
nano .env
```

填入：
```env
ARK_API_KEY=你的真实API_Key
ARK_ENDPOINT_ID=你的接入点ID
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
```

保存退出 (`Ctrl+X`, `Y`, `Enter`)

### 3.3 构建并启动

```bash
docker compose up -d --build
```

等待构建完成（首次约 1-2 分钟）。

### 3.4 验证部署

```bash
# 检查容器状态
docker compose ps

# 健康检查
curl http://localhost:8000/health
# 应返回: {"status":"ok"}

# 查看日志
docker compose logs -f --tail=50
```

### 3.5 完整功能测试

```bash
curl -X POST http://localhost:8000/api/weekly-report \
  -H "Content-Type: application/json" \
  -d '{
    "studentName": "Jinghang",
    "weekStart": "2026-05-18",
    "weekEnd": "2026-05-24",
    "metrics": {
      "studyHours": 8.8,
      "streakDays": 5,
      "questionCount": 45,
      "accuracyPct": 86.67,
      "accuracyDeltaPct": 4.17,
      "newKnowledgePoints": 7,
      "topSubject": {"name": "化学", "masteryPct": 92.0},
      "weakPoints": ["微分方程", "纯数"]
    }
  }'
```

应返回包含 `"success": true` 和完整 `data` 的 JSON。

---

## 四、Nginx 反向代理（推荐）

### 4.1 安装 Nginx

```bash
sudo apt install -y nginx
```

### 4.2 配置

```bash
sudo nano /etc/nginx/sites-available/ai-report
```

写入：
```nginx
server {
    listen 80;
    server_name 你的域名或IP;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时设置（LLM 响应可能较慢）
        proxy_read_timeout 60s;
        proxy_connect_timeout 10s;
    }
}
```

### 4.3 启用配置

```bash
sudo ln -s /etc/nginx/sites-available/ai-report /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### 4.4 HTTPS（Let's Encrypt，需域名）

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d 你的域名
```

---

## 五、防火墙配置

```bash
# 开放 HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 如果不用 Nginx，直接开放 8000
sudo ufw allow 8000/tcp

sudo ufw enable
```

---

## 六、改完代码最快重新部署

### 6.1 方案对比

| 方案 | 适用场景 | 耗时 | 命令数 |
|------|---------|------|--------|
| A. Git + 一键脚本 | 日常改动（推荐） | ~30秒 | 1条 |
| B. rsync 热同步 | 不用 Git / 本地开发直接同步 | ~10秒 | 1条 |
| C. 只改 Prompt 热更新 | 仅改 prompt_builder.py | ~5秒 | 1条 |

---

### 6.2 方案A：Git + 一键部署脚本（推荐）

在服务器创建部署脚本：

```bash
nano /opt/ai-report/deploy.sh
```

```bash
#!/bin/bash
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
```

```bash
chmod +x /opt/ai-report/deploy.sh
```

**日常使用流程（本地改完代码后）：**

```bash
# 1. 本地：提交并推送
git add .
git commit -m "fix: 修改prompt逻辑"
git push

# 2. 服务器：一键部署（SSH 执行）
ssh user@服务器IP "/opt/ai-report/deploy.sh"
```

或者更快，本地一条命令搞定：

```bash
git push && ssh user@服务器IP "/opt/ai-report/deploy.sh"
```

---

### 6.3 方案B：rsync 直接同步（不用 Git）

本地改完后直接同步文件到服务器，适合频繁调试阶段：

```bash
# Windows PowerShell（需安装 rsync 或用 scp）
scp -r D:\Ai_Report\app user@服务器IP:/opt/ai-report/

# 然后 SSH 重启
ssh user@服务器IP "cd /opt/ai-report && docker compose up -d --build"
```

或者写成本地一键脚本 `deploy-local.ps1`：

```powershell
# deploy-local.ps1 - 本地一键同步+部署
$SERVER = "user@你的服务器IP"
$REMOTE_PATH = "/opt/ai-report"

Write-Host ">>> 同步代码..." -ForegroundColor Cyan
scp -r .\app\ "${SERVER}:${REMOTE_PATH}/"
scp .\requirements.txt "${SERVER}:${REMOTE_PATH}/"
scp .\Dockerfile "${SERVER}:${REMOTE_PATH}/"

Write-Host ">>> 远程重启..." -ForegroundColor Cyan
ssh $SERVER "cd ${REMOTE_PATH} && docker compose up -d --build"

Write-Host ">>> 检查健康..." -ForegroundColor Cyan
Start-Sleep -Seconds 3
ssh $SERVER "curl -sf http://localhost:8000/health"
Write-Host "`n✅ 完成" -ForegroundColor Green
```

运行：`.\deploy-local.ps1`

---

### 6.4 方案C：只改 Prompt 热更新（最快，~5秒）

如果你只改了 `prompt_builder.py`（不涉及新依赖、不改接口签名），不需要重新 build 镜像：

```bash
# 本地推送单文件
scp D:\Ai_Report\app\prompt_builder.py user@服务器IP:/opt/ai-report/app/

# 重启容器（不 rebuild）
ssh user@服务器IP "docker compose -f /opt/ai-report/docker-compose.yml restart"
```

**注意：** 这个方案只在容器用了 volume 挂载代码目录时才生效。需要改 `docker-compose.yml`：

```yaml
services:
  weekly-report-api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./app:/app/app    # 挂载代码目录，改完文件 restart 即生效
    restart: unless-stopped
```

加上 volume 后，改 prompt 只需要：
```bash
scp app/prompt_builder.py user@IP:/opt/ai-report/app/
ssh user@IP "docker compose -f /opt/ai-report/docker-compose.yml restart"
```

5 秒搞定，不需要 rebuild。

---

### 6.5 推荐的日常工作流

```
本地改代码 → 本地跑测试 → git push → 服务器执行 deploy.sh
```

具体命令：
```bash
# 本地
python -m pytest tests/test_prompt_builder.py tests/test_edge_cases.py -q
git add . && git commit -m "描述" && git push

# 部署（一条命令）
ssh user@服务器IP "/opt/ai-report/deploy.sh"
```

全程 30 秒内完成。

## 七、日常运维

### 7.1 查看日志

```bash
# 实时日志
docker compose logs -f

# 最近100行
docker compose logs --tail=100
```

### 7.2 重启服务

```bash
docker compose restart
```

### 7.3 停止服务

```bash
docker compose down
```

### 7.4 查看资源占用

```bash
docker stats
```

---

## 八、监控与告警（可选）

### 8.1 简单存活检测 (cron)

```bash
crontab -e
```

添加：
```cron
*/5 * * * * curl -sf http://localhost:8000/health || docker compose -f /opt/ai-report/docker-compose.yml restart
```

每 5 分钟检查健康端点，失败自动重启。

### 8.2 日志持久化

修改 `docker-compose.yml`，添加日志配置：
```yaml
services:
  weekly-report-api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## 九、回滚方案

```bash
cd /opt/ai-report

# 查看历史版本
git log --oneline -10

# 回滚到指定版本
git checkout <commit-hash>
docker compose up -d --build

# 或直接回滚上一版
git revert HEAD
docker compose up -d --build
```

---

## 十、常见问题排查

| 问题 | 排查步骤 |
|------|---------|
| 容器启动失败 | `docker compose logs` 看错误 |
| API 返回 500 | 检查 `.env` 文件是否配置正确 |
| 连接火山方舟超时 | `curl https://ark.cn-beijing.volces.com` 验证网络 |
| 返回非 JSON 格式 | LLM 偶发问题，重试即可 |
| 端口被占用 | `lsof -i :8000` 查看，kill 或改端口 |
| 内存不足 OOM | `docker stats` 检查，升级服务器 |

---

## 十一、部署检查清单

- [ ] 服务器 Docker 已安装
- [ ] 代码已上传到 /opt/ai-report
- [ ] .env 文件已配置（API Key + Endpoint ID）
- [ ] `docker compose up -d --build` 成功
- [ ] `curl /health` 返回 200
- [ ] 完整功能测试通过
- [ ] 防火墙已开放对应端口
- [ ] （可选）Nginx 反代已配置
- [ ] （可选）HTTPS 已启用
- [ ] （可选）存活监控已配置
