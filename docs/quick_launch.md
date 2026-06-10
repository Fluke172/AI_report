# AI 学习周报服务快速上线手册

## 1. 上线前确认

- 已准备火山方舟 `ARK_API_KEY`
- 已准备对应模型接入点 `ARK_ENDPOINT_ID`
- 目标机器已安装 Docker 与 Docker Compose；如果走本地 Python 方式，需安装 Python 3.11+
- 已开放服务端口 `8000`

## 2. 必填环境变量

在项目根目录创建 `.env` 文件，至少包含：

```env
ARK_API_KEY=你的火山方舟APIKey
ARK_ENDPOINT_ID=你的模型接入点ID
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
```

## 3. 推荐上线方式：Docker

在项目根目录执行：

```bash
docker compose up -d --build
```

查看服务状态：

```bash
docker compose ps
```

查看启动日志：

```bash
docker compose logs -f
```

## 4. 备选方式：本地直启

安装依赖：

```bash
pip install -r requirements.txt
```

启动服务：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 5. 上线后验收

### 5.1 健康检查

```bash
curl http://localhost:8000/health
```

预期返回：

```json
{"status":"ok"}
```

### 5.2 接口冒烟

```bash
curl -X POST http://localhost:8000/api/weekly-report \
  -H "Content-Type: application/json" \
  -d '{
    "studentName": "测试学生",
    "weekStart": "2026-05-18",
    "weekEnd": "2026-05-24",
    "metrics": {
      "studyHours": 5.0,
      "streakDays": 3,
      "questionCount": 30,
      "accuracyPct": 75.0,
      "accuracyDeltaPct": 2.0,
      "newKnowledgePoints": 4,
      "weeklyTaskCompletionRatePct": 78.5,
      "topSubject": {"name": "数学", "masteryPct": 80.0},
      "weakPoints": ["函数", "应用题"]
    }
  }'
```

验收重点：

- `success` 为 `true`
- 返回 `learningHighlights` / `nextWeekSuggestions` / `studentProgress` / `warmTips` / `encouragementMessage`
- 当 `weeklyTaskCompletionRatePct >= 50` 时，`learningHighlights` 中应体现任务完成率达标
- `encouragementMessage` 末尾为 `🚀`

## 6. 本次版本关键能力

- Prompt 已补强，加入 few-shot 示例
- LLM 输出已接入严格 JSON 解析与 Pydantic 结构校验
- 已增加业务规则校验
- 当本周任务完成率 `>= 50%` 时，最终亮点必须体现该信息
- LLM 首次输出不合格时会自动重试一次
- 连续失败时会走本地 fallback，保证主链路有稳定结构化返回

## 7. 建议上线顺序

- 先在测试环境配置 `.env`
- 先执行健康检查
- 再执行一次接口冒烟
- 确认日志无 `ARK_API_KEY` / `ARK_ENDPOINT_ID` 配置错误
- 最后再切正式流量

## 8. 常见问题

### 8.1 返回 500

优先检查：

- `.env` 是否生效
- `ARK_API_KEY` 是否有效
- `ARK_ENDPOINT_ID` 是否正确
- 服务是否成功读取到环境变量

### 8.2 模型输出偶发不稳定

当前版本已内置：

- 严格解析
- 结构化校验
- 业务规则校验
- 一次重试
- 本地 fallback

如果接口仍成功但文案偏保守，通常说明已进入 fallback 兜底流程。

## 9. 回滚方式

如果需要快速回滚：

```bash
docker compose down
docker compose up -d --build
```

如需回滚到旧代码版本，请先切回对应代码版本，再重新执行上述命令。
