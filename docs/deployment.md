# AI 学习周报服务 - 部署文档

## 一、项目概述

AI 学习周报生成服务，接收学生每周学习数据，调用豆包 2.0 Lite 模型（火山方舟），返回结构化的学习周报（学习亮点、下周建议、鼓励寄语）。

- 技术栈：Python 3.11 + FastAPI + OpenAI SDK（兼容火山方舟）
- 部署方式：Docker + docker-compose
- 对外端口：8000

---

## 二、前置条件

### 2.1 服务器要求
- Docker 20.10+ 已安装
- docker-compose v2+ 已安装
- 网络可访问 `ark.cn-beijing.volces.com`（火山方舟 API）

### 2.2 火山方舟账号准备

1. 注册/登录 [火山方舟控制台](https://console.volcengine.com/ark)
2. 创建 API Key（「API Key 管理」页面）
3. 创建模型接入点（「模型推理」→「创建接入点」→ 选择 `doubao-lite-32k`）
4. 记录 Endpoint ID

---

## 三、部署步骤

### 3.1 上传代码到服务器

```bash
# 方式1: git
git clone <your-repo-url> /opt/ai-report
cd /opt/ai-report

# 方式2: scp
scp -r D:\Ai_Report user@server:/opt/ai-report
ssh user@server
cd /opt/ai-report
```

### 3.2 配置环境变量

```bash
cp .env.example .env
vim .env
```

填入真实值：
```env
ARK_API_KEY=你的API Key
ARK_ENDPOINT_ID=你的接入点ID
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
```

### 3.3 构建并启动

```bash
docker compose up -d --build
```

### 3.4 验证服务

```bash
# 健康检查
curl http://localhost:8000/health
# 预期输出: {"status":"ok"}

# 查看容器日志
docker compose logs -f --tail=50
```

### 3.5 停止/重启

```bash
docker compose down        # 停止
docker compose restart     # 重启
docker compose up -d --build  # 重新构建并启动
```

---

## 四、接口说明

### POST /api/weekly-report

**请求体示例：**
```json
{
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
    "weeklyTaskCompletionRatePct": 78.5,
    "topSubject": {"name": "化学", "masteryPct": 92.0},
    "weakPoints": ["微分方程", "纯数"],
    "rankings": {
      "diligence": {"rank": 12, "totalUsers": 356},
      "accuracy": {"rank": 8, "totalUsers": 356},
      "taskCompletion": {"rank": 15, "totalUsers": 356}
    }
  },
  "rules": {
    "highlightsMinCount": 4,
    "highlightMustPrefix": "✅",
    "suggestionsCount": 4,
    "suggestionsOrder": ["延续优势科目","专项弱项突破","增加学习时间","学习方法升级"],
    "encouragementMustInclude": {
      "name": true,
      "affirmWordsAnyOf": ["节奏", "热情", "努力"],
      "futureWordsAnyOf": ["下周", "未来"]
    }
  }
}
```

**成功响应：**
```json
{
  "success": true,
  "data": {
    "learningHighlights": [
      "✅ 本周学习时长达 8.8 小时，学习节奏稳定向好",
      "✅ 完成 45 道题目，正确率高达 86.67%，答题质量优秀",
      "✅ 新掌握 7 个知识点，知识储备持续扩展",
      "✅ 化学科目表现亮眼，掌握度达 92%",
      "✅ 正确率较上周提升 4.17%，进步明显",
      "✅ 连续学习 5 天，学习习惯越来越好",
      "✅ 精准榜第8名，实力得到认可！"
    ],
    "nextWeekSuggestions": [
      "1. 继续深化化学的学习，巩固已掌握的知识点",
      "2. 针对微分方程、纯数进行专项训练，重点突破难点",
      "3. 建议每天增加 30 分钟的复习时间，巩固本周所学内容",
      "4. 尝试用思维导图整理各科知识体系，形成完整的知识网络"
    ],
    "studentProgress": "Jinghang 本周在学习节奏、答题质量和知识吸收上都有明显进步，能看出孩子正在形成更稳定的学习状态。",
    "warmTips": "家长可以继续肯定孩子已经做到的部分，再陪孩子选择一个小目标轻量复盘，让进步在稳定节奏中慢慢累积。",
    "encouragementMessage": "Jinghang，你已经掌握了学习的节奏。保持这份热情，下周会有更大的收获！🚀"
  },
  "error": null
}
```

**失败响应：**
```json
{
  "success": false,
  "data": null,
  "error": "生成周报失败: ARK_API_KEY 环境变量未设置"
}
```

---

## 五、常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 422 Validation Error | 请求体字段缺失或类型错误 | 检查 JSON 格式 |
| 500 ARK_API_KEY 未设置 | .env 文件未配置 | 检查 .env |
| 连接超时 | 服务器无法访问火山方舟 | 检查网络/防火墙 |
| JSON 解析失败 | 模型返回非 JSON 格式 | 重试或调低 temperature |

---

## 六、更新部署

```bash
cd /opt/ai-report
git pull
docker compose up -d --build
```
