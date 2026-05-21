# AI 学习周报生成服务

输入学生每周学习数据，调用豆包 2.0 Lite 模型生成包含**学习亮点、下周建议、鼓励寄语**的 AI 周报。

## 快速部署

### 1. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入火山方舟的 API Key 和 Endpoint ID：

```
ARK_API_KEY=你的API Key
ARK_ENDPOINT_ID=你的接入点ID
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
```

> **获取方式：**
> 1. 登录 [火山方舟控制台](https://console.volcengine.com/ark)
> 2. 创建 API Key
> 3. 在「模型推理」页面创建接入点，选择 `doubao-lite-32k` 模型，获取 Endpoint ID

### 2. Docker 部署（推荐）

```bash
docker compose up -d --build
```

服务运行在 `http://localhost:8000`

### 3. 本地开发

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## API 文档

启动后访问：`http://localhost:8000/docs`

### POST /api/weekly-report

**请求示例：**

```json
{
  "student_name": "小秋",
  "week_start": "04/04",
  "week_end": "04/10",
  "total_hours": 12.5,
  "total_questions": 1248,
  "avg_accuracy": 82.0,
  "last_week_accuracy": 79.0,
  "new_knowledge_points": 18,
  "consecutive_days": 5,
  "subjects": [
    {"name": "数学", "mastery": 88.0, "questions_count": 520, "accuracy": 85.0},
    {"name": "英语", "mastery": 72.0, "questions_count": 380, "accuracy": 78.0},
    {"name": "语文", "mastery": 65.0, "questions_count": 348, "accuracy": 80.0}
  ],
  "weak_points": ["分数运算", "几何证明"]
}
```

**响应示例：**

```json
{
  "success": true,
  "report": "本周（04/04 - 04/10），小秋 同学表现稳定，学习态度认真...\n\n⭐ 学习亮点\n✓ 本周学习时长达 12.5 小时...\n\n🎯 下周建议\n1. 继续深化数学的学习...\n\n💖 鼓励寄语\n小秋，你已经掌握了学习的节奏..."
}
```

## 周报生成规则

### 学习亮点（自动选取 ≥4 条）
| 维度 | 触发条件 | 输出模板 |
|------|---------|---------|
| 学习时长 | ≥1h | 本周学习时长达 X 小时，保持稳定的学习节奏 |
| 做题量 | ≥10题 | 完成 X 道题目，正确率 Y% |
| 新知识点 | ≥1个 | 新学习 X 个知识点，知识面不断扩展 |
| 科目表现 | 掌握度≥50% | X科目表现突出，掌握度达 Y% |
| 正确率提升 | 相比上周≥1% | 整体正确率稳步提升，学习效果显著 |
| 连续学习 | ≥2天 | 连续学习状态良好，养成稳定学习习惯 |
| 每周任务完成情况 | 本周任务完成率≥50% | 本周任务完成率达到 X%，任务执行情况良好 |
| 排行榜榜单 | 任一榜单 rank≤10 | 本周排行榜表现亮眼：XX榜第N名 |

### 下周建议（固定4条，按优先级）
1. 延续优势科目
2. 专项弱项突破
3. 增加学习时间
4. 学习方法升级（固定）

### 鼓励寄语
包含学生姓名，肯定节奏/热情/努力，指向下周/未来。
