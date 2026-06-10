# AI 学习周报生成服务 - 第三方交接文档

## 一、项目信息

| 项目 | 信息 |
|------|------|
| 项目名称 | AI 学习周报生成服务 |
| 版本 | 2.0.0 |
| 技术栈 | Python 3.11 + FastAPI + 豆包 2.0 Lite (火山方舟) |
| 部署方式 | Docker + docker-compose |
| 协议 | HTTP REST API |
| 端口 | 8000 |

---

## 二、项目结构

```
D:\Ai_Report/
├── app/                          # 应用主代码
│   ├── __init__.py
│   ├── main.py                   # FastAPI 入口，路由定义
│   ├── models.py                 # Pydantic 数据模型（请求/响应）
│   ├── prompt_builder.py         # 规则引擎 + Prompt 构造逻辑
│   └── llm_client.py             # 豆包模型调用封装
├── tests/                        # 测试代码
│   ├── __init__.py
│   ├── test_prompt_builder.py    # 单元测试（59 cases）
│   ├── test_edge_cases.py        # 边界+集成测试（29 cases）
│   └── test_verbose.py           # 可视化场景测试（独立运行）
├── docs/                         # 文档
│   ├── deployment.md             # 部署文档
│   └── handover.md               # 本文档
├── .env.example                  # 环境变量模板
├── .dockerignore
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 三、核心架构

```
┌─────────────┐     ┌──────────────────┐     ┌────────────────────┐
│   前端/调用方  │────▶│  FastAPI 服务     │────▶│  豆包 2.0 Lite     │
│  POST JSON   │     │  (main.py)       │     │  (火山方舟 API)     │
└─────────────┘     └──────────────────┘     └────────────────────┘
                           │
                    ┌──────┴──────┐
                    ▼             ▼
             规则引擎          LLM 客户端
         (prompt_builder)    (llm_client)
```

**数据流：**
1. 前端 POST 学习数据 JSON → FastAPI 接口
2. `prompt_builder.py` 规则引擎根据数据+规则生成亮点/建议素材
3. 构造 system prompt + user prompt
4. `llm_client.py` 调用豆包模型，获取 JSON 格式输出
5. 解析 JSON，返回结构化响应

---

## 四、接口规格

### 4.1 健康检查

```
GET /health
Response: {"status": "ok"}
```

### 4.2 生成周报

```
POST /api/weekly-report
Content-Type: application/json
```

**请求体结构：**

```json
{
  "studentName": "string (必填, 学生姓名)",
  "weekStart": "string (必填, yyyy-MM-dd, 周一)",
  "weekEnd": "string (必填, yyyy-MM-dd, 周日)",
  "metrics": {
    "studyHours": "float (必填, 本周学习时长/小时)",
    "streakDays": "int (必填, ≥0, 连续学习天数)",
    "questionCount": "int (必填, 做题总数)",
    "accuracyPct": "float (必填, 0-100, 本周正确率%)",
    "accuracyDeltaPct": "float (默认0, 较上周变化, 正=提升)",
    "newKnowledgePoints": "int (必填, 新知识点数)",
    "weeklyTaskCompletionRatePct": "float? (可选, 0-100, 任务完成率)",
    "topSubject": {
      "name": "string (必填, 优势科目)",
      "masteryPct": "float (必填, 0-100, 掌握度)"
    },
    "weakPoints": ["string? (可选, 薄弱知识点列表)"],
    "rankings": {
      "diligence": {"rank": "int", "totalUsers": "int"},
      "accuracy": {"rank": "int", "totalUsers": "int"},
      "taskCompletion": {"rank": "int", "totalUsers": "int"}
    }
  },
  "rules": {
    "highlightsMinCount": "int (默认4, 亮点最少条数)",
    "highlightMustPrefix": "string (默认'✅', 亮点前缀)",
    "suggestionsCount": "int (默认4, 建议条数)",
    "suggestionsOrder": ["string (默认4条顺序)"],
    "encouragementMustInclude": {
      "name": "bool (默认true)",
      "affirmWordsAnyOf": ["string (默认: 节奏/热情/努力)"],
      "futureWordsAnyOf": ["string (默认: 下周/未来)"]
    }
  }
}
```

**成功响应 (200)：**

```json
{
  "success": true,
  "data": {
    "learningHighlights": ["✅ 亮点文案1", "✅ 亮点文案2", ...],
    "nextWeekSuggestions": ["1. 建议1", "2. 建议2", "3. 建议3", "4. 建议4"],
    "studentProgress": "面向家长的学生进步与优秀表现反馈",
    "warmTips": "面向家长的温馨陪伴建议",
    "encouragementMessage": "姓名，鼓励寄语...🚀"
  },
  "error": null
}
```

**验证失败 (422)：** 请求体格式错误
**服务器错误 (500)：** 环境变量未配置

---

## 五、业务规则说明

### 5.1 学习亮点生成规则

从以下 8 个维度自动评估，满足条件即纳入亮点素材：

| # | 维度 | 触发条件 | 素材模板 |
|---|------|---------|---------|
| 1 | 学习时长 | ≥ 1h | 本周学习时长达 X 小时 |
| 2 | 做题量 | ≥ 10题 | 完成 X 道题目，正确率 Y% |
| 3 | 新知识点 | ≥ 1个 | 新学习 X 个知识点 |
| 4 | 科目表现 | 掌握度 ≥ 50% | X科目表现突出，掌握度达Y% |
| 5 | 正确率提升 | 环比 ≥ 1% | 整体正确率提升X%，效果明显 |
| 6 | 连续学习 | ≥ 2天 | 连续学习X天，养成稳定习惯 |
| 7 | 每周任务完成情况 | 本周任务完成率 ≥ 50% | 本周任务完成率达到 X%，任务执行情况良好 |
| 8 | 排行榜 | rank ≤ 10 | 排行榜表现亮眼：XX榜第N名 |

- 最终亮点数量 ≥ `rules.highlightsMinCount`
- 不足时从 5 条通用兜底文案中补充
- 排行榜多个进前10合并为1条
- 当 `weeklyTaskCompletionRatePct >= 50` 时，最终结构化输出中的 `learningHighlights` 必须体现“任务完成率达标”

### 5.2 下周建议生成规则

固定 4 条，按优先级：

| # | 方向 | 逻辑 |
|---|------|------|
| 1 | 延续优势科目 | 取 topSubject.name |
| 2 | 专项弱项突破 | 有 weakPoints 取前2个；无则通用 |
| 3 | 增加学习时间 | < 15h 建议增加；≥ 15h 保持 |
| 4 | 学习方法升级 | 固定：思维导图 |

### 5.3 鼓励寄语约束

- 必须包含 `studentName`
- 必须包含 `affirmWordsAnyOf` 中至少一个词
- 必须包含 `futureWordsAnyOf` 中至少一个词
- 末尾加 🚀

---

## 六、依赖与环境变量

### 6.1 Python 依赖

```
fastapi==0.115.6
uvicorn==0.34.0
openai==1.58.1
pydantic==2.10.3
python-dotenv==1.0.1
```

### 6.2 环境变量

| 变量名 | 必填 | 说明 |
|--------|------|------|
| ARK_API_KEY | 是 | 火山方舟 API Key |
| ARK_ENDPOINT_ID | 是 | 豆包模型接入点 ID |
| ARK_BASE_URL | 否 | 默认 https://ark.cn-beijing.volces.com/api/v3 |

---

## 七、测试覆盖

| 测试文件 | 用例数 | 覆盖范围 |
|----------|--------|---------|
| test_prompt_builder.py | 59 | 规则引擎、模型验证、Prompt构建、集成场景、API端点 |
| test_edge_cases.py | 29 | LLM JSON解析、Mock集成、极端值、自定义规则、排行榜组合、安全 |
| test_verbose.py | 8场景 | 可视化验证（独立运行） |
| **总计** | **88 + 8** | - |

运行测试：
```bash
# 自动化测试（CI/CD 用）
python -m pytest tests/test_prompt_builder.py tests/test_edge_cases.py -v

# 可视化详细测试（人工查看）
python tests/test_verbose.py
```

---

## 八、已知限制

1. LLM 输出不是 100% 确定性的，偶尔可能格式偏差（已做严格 JSON 解析、结构校验、一次重试和本地兜底）
2. 亮点规则引擎兜底文案只有 5 条；但主链路在 LLM 连续失败时会走本地 fallback，保证返回结构可用
3. `weakPoints` 建议中只取前 2 个展示
4. 目前无鉴权中间件，生产建议加 API Key 或 JWT 验证
5. 无请求限流，高并发场景建议加 Nginx + rate limit

---

## 九、后续优化建议

1. 加入鉴权中间件（API Key / JWT）
2. 加入请求限流（防止 LLM 费用失控）
3. 加入响应缓存（同一学生同一周数据缓存结果）
4. LLM 输出做二次验证（检查是否包含必填词）
5. 加入结构化日志（方便排查问题）
6. 考虑流式响应（SSE）用于前端实时展示
