"""根据学习数据和动态规则构建 prompt
输入结构完全对齐前端传入的 JSON
"""

from app.models import WeeklyReportRequest


def build_highlights_material(req: WeeklyReportRequest) -> list[str]:
    """
    学习亮点素材生成（规则引擎）
    从以下维度自动选取，确保 ≥ rules.highlightsMinCount 条：
    1. 学习时长 ≥1h
    2. 做题量 ≥10题
    3. 新知识点 ≥1个
    4. 科目表现 掌握度≥50%
    5. 正确率提升 ≥1%
    6. 连续学习天数 ≥2天
    7. 本周任务完成率 ≥50%
    8. 排行榜前10
    """
    m = req.metrics
    highlights = []

    # 维度1: 学习时长
    if m.studyHours >= 1:
        highlights.append(f"本周学习时长达 {m.studyHours} 小时，保持稳定的学习节奏")

    # 维度2: 做题量
    if m.questionCount >= 10:
        highlights.append(f"完成 {m.questionCount} 道题目，平均正确率 {m.accuracyPct}%")

    # 维度3: 新知识点
    if m.newKnowledgePoints >= 1:
        highlights.append(f"新学习 {m.newKnowledgePoints} 个知识点，知识面不断扩展")

    # 维度4: 优势科目掌握度≥50%
    if m.topSubject.masteryPct >= 50:
        highlights.append(f"{m.topSubject.name} 科目表现突出，掌握度达 {m.topSubject.masteryPct}%")

    # 维度5: 正确率提升≥1%
    if m.accuracyDeltaPct >= 1:
        highlights.append(f"整体正确率较上周提升 {m.accuracyDeltaPct}%，学习效果明显")

    # 维度6: 连续学习天数≥2天
    if m.streakDays >= 2:
        highlights.append(f"连续学习 {m.streakDays} 天，学习状态良好，养成稳定习惯")

    # 维度7: 本周任务完成率≥50%
    if m.weeklyTaskCompletionRatePct is not None and m.weeklyTaskCompletionRatePct >= 50:
        highlights.append(f"本周任务完成率达到 {m.weeklyTaskCompletionRatePct}%，任务执行情况良好")

    # 维度8: 排行榜前10
    if m.rankings:
        rank_items = []
        if m.rankings.diligence and m.rankings.diligence.rank <= 10:
            rank_items.append(f"勤学榜第{m.rankings.diligence.rank}名")
        if m.rankings.accuracy and m.rankings.accuracy.rank <= 10:
            rank_items.append(f"精准榜第{m.rankings.accuracy.rank}名")
        if m.rankings.taskCompletion and m.rankings.taskCompletion.rank <= 10:
            rank_items.append(f"任务榜第{m.rankings.taskCompletion.rank}名")
        if rank_items:
            highlights.append(f"本周排行榜表现亮眼：{'、'.join(rank_items)}，值得点赞")

    # 兜底：不足 min_count 时补充通用亮点
    min_count = req.rules.highlightsMinCount
    fallbacks = [
        "学习态度认真，按时完成学习计划",
        "积极面对学习挑战，不轻言放弃",
        "学习主动性强，能够自主安排学习时间",
        "坚持参与每周学习，保持学习连续性",
        "敢于挑战新题型，勇于突破自我",
    ]
    idx = 0
    while len(highlights) < min_count and idx < len(fallbacks):
        highlights.append(fallbacks[idx])
        idx += 1

    return highlights


def build_suggestions_material(req: WeeklyReportRequest) -> list[str]:
    """
    下周建议素材生成（规则引擎）
    固定4条，按 rules.suggestionsOrder 优先级：
    1. 延续优势科目
    2. 专项弱项突破
    3. 增加学习时间
    4. 学习方法升级
    """
    m = req.metrics
    suggestions = []

    # 1. 延续优势科目
    suggestions.append(f"继续深化 {m.topSubject.name} 的学习，巩固已掌握的知识点")

    # 2. 专项弱项突破
    if m.weakPoints and len(m.weakPoints) > 0:
        weak_str = "、".join(m.weakPoints[:2])
        suggestions.append(f"针对正确率较低的知识点（{weak_str}）进行专项训练，重点突破难点")
    else:
        suggestions.append("针对易错题型进行专项训练，进一步减少失误")

    # 3. 增加学习时间
    if m.studyHours < 15:
        suggestions.append("建议每天增加 30 分钟的复习时间，巩固本周所学内容")
    else:
        suggestions.append("继续保持现有学习节奏，适当增加限时训练")

    # 4. 学习方法升级（固定）
    suggestions.append("尝试用思维导图整理各科知识体系，形成完整的知识网络")

    return suggestions


def build_student_progress_material(req: WeeklyReportRequest) -> str:
    """生成面向家长的学生进步与优秀表现素材"""
    m = req.metrics
    parts = []

    if m.accuracyDeltaPct >= 1:
        parts.append(f"综合正确率较上周提升 {m.accuracyDeltaPct}%")
    if m.weeklyTaskCompletionRatePct is not None and m.weeklyTaskCompletionRatePct >= 50:
        parts.append(f"任务完成率达到 {m.weeklyTaskCompletionRatePct}%")
    if m.streakDays >= 2:
        parts.append(f"连续学习 {m.streakDays} 天")
    if m.topSubject.masteryPct >= 50:
        parts.append(f"{m.topSubject.name} 掌握度达到 {m.topSubject.masteryPct}%")
    if m.newKnowledgePoints >= 1:
        parts.append(f"新增学习 {m.newKnowledgePoints} 个知识点")
    if m.questionCount >= 10:
        parts.append(f"完成 {m.questionCount} 道题目练习")

    if not parts:
        parts.append("本周能持续参与学习，并愿意面对当前阶段的练习任务")

    return "；".join(parts)


def build_warm_tips_material(req: WeeklyReportRequest) -> str:
    """生成面向家长的温馨陪伴建议素材"""
    m = req.metrics

    if m.weakPoints:
        weak_str = "、".join(m.weakPoints[:2])
        return f"家长可以陪孩子轻量复盘 {weak_str} 相关错题，先鼓励孩子说出解题思路，再一起找到一个小突破口"

    if m.accuracyDeltaPct < 0:
        return "正确率有波动时，家长可以先肯定孩子愿意继续练习的态度，再陪孩子一起看错因，减少焦虑感"

    if m.studyHours < 15:
        return "家长可以帮助孩子固定一段轻量复盘时间，不必一次安排太满，先让孩子把学习节奏稳定下来"

    return "家长可以继续肯定孩子的坚持和自律，适当让孩子自己总结本周有效的方法，增强学习自主感"


def build_output_few_shot_example(req: WeeklyReportRequest) -> str:
    prefix = req.rules.highlightMustPrefix
    return f'''{{
  "learningHighlights": [
    "{prefix} 本周保持稳定学习节奏，基础表现扎实",
    "{prefix} 优势科目掌握较好，学习成果持续巩固",
    "{prefix} 连续学习状态在线，执行力值得肯定",
    "{prefix} 新知识点吸收顺利，知识面继续拓展"
  ],
  "nextWeekSuggestions": [
    "继续巩固优势科目的核心知识点",
    "围绕薄弱知识点安排专项突破训练",
    "每天预留固定复盘时间巩固错题",
    "用思维导图整理重点内容提升方法"
  ],
  "studentProgress": "示例同学本周能保持稳定投入，在学习节奏和知识吸收上都有值得肯定的进步，也能更主动地面对练习任务。",
  "warmTips": "家长可以继续多肯定孩子已经做到的部分，再陪孩子选择一个小目标坚持复盘，让进步在轻松稳定的节奏里慢慢累积。",
  "encouragementMessage": "示例同学，这周的努力和学习节奏值得肯定，期待你下周继续稳步进步🚀"
}}'''


def build_system_prompt(req: WeeklyReportRequest) -> str:
    """构建系统提示词 - 基于动态 rules 约束"""
    rules = req.rules
    prefix = rules.highlightMustPrefix
    affirm_words = "/".join(rules.encouragementMustInclude.affirmWordsAnyOf)
    future_words = "/".join(rules.encouragementMustInclude.futureWordsAnyOf)
    few_shot_example = build_output_few_shot_example(req)

    return f"""# 角色
你是一位专业的 K12 国际学校教育 AI 学习周报撰写助手。根据提供的学习数据和素材，生成温暖、专业、有针对性的学习周报内容。

# 输出要求
你需要输出一个严格的 JSON 对象，包含以下五个字段：

## 1. learningHighlights（学习亮点数组）
- 数组长度 ≥ {rules.highlightsMinCount}
- 每条以「{prefix}」开头
## 2. nextWeekSuggestions（下周建议数组）
- 固定 {rules.suggestionsCount} 条
- 顺序为：{" → ".join(rules.suggestionsOrder)}
## 3. studentProgress（学生进步与优秀表现字符串）
- 面向家长阅读，概括学生本周的进步、努力和做得好的地方
- 语气像老师与家长沟通，温和、具体、不过度夸张
- 控制在 40-90 字
## 4. warmTips（温馨小贴士字符串）
- 面向家长阅读，给出家庭陪伴或学习支持建议
- 用“可以”“建议”等柔和表达，避免责备、施压或制造焦虑
- 控制在 40-90 字
## 5. encouragementMessage（鼓励寄语字符串）
- 必须包含学生姓名
- 必须包含以下词语之一：{affirm_words}
- 必须包含以下词语之一：{future_words}
- 语气温暖积极，像一位关心学生的班主任
- 末尾加 🚀 emoji

# 约束
1. 只输出 JSON，不要输出任何其他文本、解释或 markdown 格式
2. JSON 必须可直接解析，不要用 ```json ``` 包裹
3. 字段名必须严格使用 learningHighlights、nextWeekSuggestions、studentProgress、warmTips、encouragementMessage
4. 五个字段都必须出现，不能缺失，不能输出 null，不能新增其他字段
5. learningHighlights 和 nextWeekSuggestions 必须是字符串数组，studentProgress、warmTips、encouragementMessage 必须是字符串
6. 数据必须与输入一致，不可编造
7. 语言自然流畅不机械化，有温度有个性
8. 每条亮点和建议控制在 15-40 字

# 输出示例
以下示例只演示格式，不可照抄内容：
{few_shot_example}"""


def build_user_prompt(req: WeeklyReportRequest) -> str:
    """构建用户提示词"""
    m = req.metrics
    highlights = build_highlights_material(req)
    suggestions = build_suggestions_material(req)
    student_progress_material = build_student_progress_material(req)
    warm_tips_material = build_warm_tips_material(req)

    prefix = req.rules.highlightMustPrefix
    highlights_text = "\n".join(f"{prefix} {h}" for h in highlights)
    suggestions_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(suggestions))

    # 排行榜信息
    ranking_text = "未进入前10名"
    if m.rankings:
        parts = []
        if m.rankings.diligence:
            r = m.rankings.diligence
            status = f"第{r.rank}名/{r.totalUsers}人" + (" ⭐前10" if r.rank <= 10 else "")
            parts.append(f"勤学榜: {status}")
        if m.rankings.accuracy:
            r = m.rankings.accuracy
            status = f"第{r.rank}名/{r.totalUsers}人" + (" ⭐前10" if r.rank <= 10 else "")
            parts.append(f"精准榜: {status}")
        if m.rankings.taskCompletion:
            r = m.rankings.taskCompletion
            status = f"第{r.rank}名/{r.totalUsers}人" + (" ⭐前10" if r.rank <= 10 else "")
            parts.append(f"任务榜: {status}")
        if parts:
            ranking_text = "\n".join(f"  - {p}" for p in parts)

    # 任务完成率
    task_text = "无数据"
    if m.weeklyTaskCompletionRatePct is not None:
        task_text = f"{m.weeklyTaskCompletionRatePct}%"

    # 正确率变化
    if m.accuracyDeltaPct > 0:
        accuracy_trend = f"↑{m.accuracyDeltaPct}%"
    elif m.accuracyDeltaPct < 0:
        accuracy_trend = f"↓{abs(m.accuracyDeltaPct)}%"
    else:
        accuracy_trend = "持平"

    prompt = f"""请为以下学生生成学习周报 JSON。严格基于素材润色，不编造数据。

━━━━━━ 学生信息 ━━━━━━
姓名：{req.studentName}
统计周期：{req.weekStart} ~ {req.weekEnd}

━━━━━━ 核心指标 ━━━━━━
学习时长：{m.studyHours} 小时
连续学习：{m.streakDays} 天
做题总数：{m.questionCount} 道
综合正确率：{m.accuracyPct}%（较上周 {accuracy_trend}）
新增知识点：{m.newKnowledgePoints} 个
任务完成率：{task_text}
优势科目：{m.topSubject.name}（掌握度 {m.topSubject.masteryPct}%）
薄弱知识点：{"、".join(m.weakPoints) if m.weakPoints else "无"}

━━━━━━ 排行榜 ━━━━━━
{ranking_text}

━━━━━━ 学习亮点素材（请润色后输出，≥{req.rules.highlightsMinCount}条） ━━━━━━
{highlights_text}

━━━━━━ 下周建议素材（固定{req.rules.suggestionsCount}条） ━━━━━━
{suggestions_text}

━━━━━━ 家长可见字段素材 ━━━━━━
学生进步与优秀表现素材：{student_progress_material}
温馨小贴士素材：{warm_tips_material}

━━━━━━ 家长可见字段语气要求 ━━━━━━
- studentProgress 和 warmTips 都给家长阅读，语气要像老师和家长之间的温和沟通
- 既肯定学生已经做到的地方，也给出可执行、不过度施压的家庭支持建议
- 不要使用批评、命令式或制造焦虑的表达

━━━━━━ 鼓励寄语要求 ━━━━━━
- 必须包含姓名「{req.studentName}」
- 必须包含「{"/".join(req.rules.encouragementMustInclude.affirmWordsAnyOf)}」之一
- 必须包含「{"/".join(req.rules.encouragementMustInclude.futureWordsAnyOf)}」之一
- 末尾加 🚀

请输出 JSON："""

    return prompt
