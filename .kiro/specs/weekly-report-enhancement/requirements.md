# Requirements Document

## Introduction

对现有 AI 学习周报生成服务的功能增强。当前系统已具备基础的学习亮点、下周建议、鼓励寄语生成能力。本次增量需求需覆盖：学习亮点多维度选取规则完善、每日任务完成情况板块新增、排行榜前10名在周报中的赞扬体现、下周建议固定四条结构化输出、鼓励寄语包含学生姓名及情感要素。同时要求最终文案"不要机械化"，AI 可灵活润色。

## Glossary

- **Weekly_Report_Service**: AI 学习周报生成 FastAPI 后端服务
- **Prompt_Builder**: 根据学习数据构建 LLM 提示词的模块（prompt_builder.py）
- **LLM_Client**: 调用豆包2.0 Lite 模型生成文本的客户端模块（llm_client.py）
- **WeeklyStudyData**: 每周学习数据的输入模型，包含学生基本信息、学习指标、科目数据、排行榜及每日任务等字段
- **Highlights_Generator**: Prompt_Builder 中负责生成学习亮点素材的子逻辑
- **Suggestions_Generator**: Prompt_Builder 中负责生成下周建议素材的子逻辑
- **DailyTaskSummary**: 每日任务完成概况数据模型，包含推送任务数、完成任务数、完成率
- **RankingData**: 排行榜数据模型，包含勤学时长榜、任务先锋榜、精准作答榜的排名
- **Student_Name**: 输入数据中的学生姓名字段

## Requirements

### Requirement 1: 学习亮点多维度自动选取

**User Story:** As a 产品运营人员, I want 系统从学科掌握度、连续学习、高分成就、薄弱点攻克等维度自动选取≥4条学习亮点, so that 周报能全面反映学生本周学习表现。

#### Acceptance Criteria

1. WHEN WeeklyStudyData 被提交, THE Highlights_Generator SHALL 从以下维度评估并选取亮点：学习时长（≥1h）、做题量（≥10题）、新知识点（≥1个）、科目掌握度（≥50%）、正确率提升（较上周≥1%）、连续学习天数（≥2天）、排行榜前10名
2. THE Highlights_Generator SHALL 生成不少于4条学习亮点素材
3. WHEN 满足条件的维度不足4条, THE Highlights_Generator SHALL 从预设的通用正向素材中补充至4条
4. WHEN 同一维度有多个科目满足条件, THE Highlights_Generator SHALL 选取掌握度最高的1个科目作为该维度代表
5. WHEN RankingData 中任意排行榜排名进入前10, THE Highlights_Generator SHALL 将排行榜成绩作为独立亮点条目纳入

### Requirement 2: 每日任务完成情况板块

**User Story:** As a 学生家长, I want 周报中包含每日任务推送和完成情况的板块, so that 我能了解孩子每日任务的执行情况。

#### Acceptance Criteria

1. WHEN DailyTaskSummary 数据存在于 WeeklyStudyData 中, THE Prompt_Builder SHALL 在周报输出中生成「📋 每日任务完成情况」板块
2. THE Prompt_Builder SHALL 在每日任务板块中包含本周推送任务总数、完成任务数和完成率
3. WHEN DailyTaskSummary 数据不存在, THE Weekly_Report_Service SHALL 跳过每日任务板块，不在周报中输出任何占位文本
4. WHEN 任务完成率 ≥ 80%, THE LLM_Client 生成的周报文案 SHALL 对完成情况给予肯定鼓励
5. WHEN 任务完成率 < 80%, THE LLM_Client 生成的周报文案 SHALL 以温和语气鼓励学生提升任务执行力

### Requirement 3: 排行榜前10名在周报中体现

**User Story:** As a 学生, I want 当我在勤学时长榜、任务先锋榜或精准作答榜进入前10时周报中能体现这一成绩, so that 我能感受到竞争激励和成就感。

#### Acceptance Criteria

1. WHEN RankingData 中 study_hours_rank、task_completion_rank 或 accuracy_rank 任一字段有值（非 null）, THE Highlights_Generator SHALL 将对应排行榜名称和排名纳入亮点素材
2. WHEN 学生同时进入多个排行榜前10, THE Highlights_Generator SHALL 将所有上榜信息合并为一条亮点（如"勤学时长榜第3名、任务先锋榜第5名"）
3. THE Prompt_Builder SHALL 在 system_prompt 中指示 LLM 对排行榜成绩使用赞扬鼓励语气
4. WHEN RankingData 所有排名字段均为 null, THE Highlights_Generator SHALL 不生成排行榜相关亮点条目

### Requirement 4: 下周建议结构化输出

**User Story:** As a 学生, I want 下周建议以1.2.3.4.数字列表格式呈现且覆盖四个方向, so that 我能获得清晰可执行的下周学习指引。

#### Acceptance Criteria

1. THE Suggestions_Generator SHALL 固定生成4条建议，顺序为：延续优势科目、专项弱项突破、增加学习时间、学习方法升级
2. WHEN subjects 数据存在, THE Suggestions_Generator SHALL 取掌握度最高的科目生成第1条"延续优势科目"建议
3. WHEN weak_points 存在且非空, THE Suggestions_Generator SHALL 根据薄弱知识点生成第2条"专项弱项突破"建议
4. WHEN weak_points 不存在或为空, THE Suggestions_Generator SHALL 生成针对易错题型的通用弱项突破建议
5. THE Suggestions_Generator SHALL 根据本周学习时长生成第3条"增加学习时间"建议
6. THE Suggestions_Generator SHALL 固定生成第4条"学习方法升级"建议，内容为建议使用思维导图整理知识体系
7. THE Prompt_Builder SHALL 在 user_prompt 中将4条建议以「1. 2. 3. 4.」数字列表格式呈现

### Requirement 5: 鼓励寄语包含情感要素

**User Story:** As a 学生, I want 鼓励寄语中包含我的姓名并肯定我的努力, so that 我能感受到个性化的关怀和激励。

#### Acceptance Criteria

1. THE Prompt_Builder SHALL 在鼓励寄语生成指令中要求包含 Student_Name
2. THE Prompt_Builder SHALL 在鼓励寄语生成指令中要求肯定学生的节奏、热情或努力之一
3. THE Prompt_Builder SHALL 在鼓励寄语生成指令中要求展望下周或未来
4. THE Prompt_Builder SHALL 在鼓励寄语生成指令中要求末尾附带 🚀 emoji
5. WHEN 周报生成完成, THE Weekly_Report_Service 返回的 report 文本中鼓励寄语部分 SHALL 包含输入数据中的 student_name 值

### Requirement 6: 文案自然灵活表达

**User Story:** As a 产品运营人员, I want AI生成的周报文案自然有温度不机械化, so that 学生和家长阅读时有真实感受到关怀的体验。

#### Acceptance Criteria

1. THE Prompt_Builder SHALL 在 system_prompt 中明确指示 LLM 语言要自然流畅，不要机械化套模板
2. THE Prompt_Builder SHALL 在 system_prompt 中允许 LLM 对素材进行灵活润色但不改变数据事实
3. THE Prompt_Builder SHALL 在 system_prompt 中要求保持温暖积极的语气，像一位关心学生的班主任
4. THE Prompt_Builder SHALL 在 system_prompt 中限制总字数在 350-600 字之间

### Requirement 7: 数据模型完整性

**User Story:** As a 后端开发人员, I want WeeklyStudyData 模型包含所有新需求的输入字段, so that 前端可以传入完整数据供周报生成使用。

#### Acceptance Criteria

1. THE WeeklyStudyData SHALL 包含 ranking 字段（类型为 Optional[RankingData]），用于接收排行榜数据
2. THE WeeklyStudyData SHALL 包含 daily_task 字段（类型为 Optional[DailyTaskSummary]），用于接收每日任务数据
3. THE RankingData SHALL 包含 study_hours_rank（勤学时长榜排名）、task_completion_rank（任务先锋榜排名）、accuracy_rank（精准作答榜排名）三个 Optional[int] 字段
4. THE DailyTaskSummary SHALL 包含 total_tasks（推送任务数）、completed_tasks（完成任务数）、completion_rate（完成率）三个字段
5. WHEN ranking 或 daily_task 字段未传入, THE Weekly_Report_Service SHALL 正常生成周报，对应板块跳过

### Requirement 8: 周报输出结构顺序

**User Story:** As a 前端开发人员, I want 周报输出严格按照固定板块顺序, so that 前端解析和展示时有稳定可预期的结构。

#### Acceptance Criteria

1. THE Prompt_Builder SHALL 指示 LLM 按以下顺序输出周报板块：总结导语 → ⭐ 学习亮点 → 📋 每日任务完成情况 → 🎯 下周建议 → 💖 鼓励寄语
2. THE Prompt_Builder SHALL 指示 LLM 不添加规则之外的额外章节
3. THE Prompt_Builder SHALL 指示 LLM 不使用 markdown 标题符号（#），使用纯文本加 emoji 作为板块标题
