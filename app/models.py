"""数据模型 - 严格对齐前端传入的 JSON 结构"""

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator
from typing import Optional


class TopSubject(BaseModel):
    """优势科目"""
    name: str = Field(..., description="优势科目名称", examples=["化学"])
    masteryPct: float = Field(..., description="该科目掌握度(%)", ge=0, le=100, examples=[92.0])


class RankingItem(BaseModel):
    """单个排行榜排名"""
    rank: int = Field(..., description="当前用户本周排名", examples=[8])
    totalUsers: int = Field(..., description="本周参榜总人数", examples=[356])


class Rankings(BaseModel):
    """三个排行榜排名"""
    diligence: Optional[RankingItem] = Field(None, description="勤学榜")
    accuracy: Optional[RankingItem] = Field(None, description="精准榜(正确率榜)")
    taskCompletion: Optional[RankingItem] = Field(None, description="任务榜(任务完成率榜)")


class Metrics(BaseModel):
    """周报核心指标"""
    studyHours: float = Field(..., description="本周总学习时长(小时)", examples=[8.8])
    streakDays: int = Field(..., description="本周连续学习天数", ge=0, examples=[5])
    questionCount: int = Field(..., description="本周做题总数", examples=[45])
    accuracyPct: float = Field(..., description="本周整体正确率(%)", ge=0, le=100, examples=[86.67])
    accuracyDeltaPct: float = Field(0, description="较上周正确率变化(正数为提升)", examples=[4.17])
    newKnowledgePoints: int = Field(..., description="本周新增知识点数量", examples=[7])
    weeklyTaskCompletionRatePct: Optional[float] = Field(None, description="本周任务完成率(%)", ge=0, le=100, examples=[78.5])
    topSubject: TopSubject = Field(..., description="优势科目信息")
    weakPoints: Optional[list[str]] = Field(None, description="薄弱知识点名称列表", examples=[["微分方程", "纯数"]])
    rankings: Optional[Rankings] = Field(None, description="三个排行榜排名")


class EncouragementRules(BaseModel):
    """鼓励寄语约束"""
    name: bool = Field(True, description="是否必须包含姓名")
    affirmWordsAnyOf: list[str] = Field(default=["节奏", "热情", "努力"], description="必须包含其一")
    futureWordsAnyOf: list[str] = Field(default=["下周", "未来"], description="必须包含其一")


class Rules(BaseModel):
    """文案生成约束"""
    highlightsMinCount: int = Field(4, description="学习亮点最少条数", ge=1)
    highlightMustPrefix: str = Field("✅", description="学习亮点每条前缀")
    suggestionsCount: int = Field(4, description="下周建议固定条数")
    suggestionsOrder: list[str] = Field(
        default=["延续优势科目", "专项弱项突破", "增加学习时间", "学习方法升级"],
        description="建议输出顺序"
    )
    encouragementMustInclude: EncouragementRules = Field(default_factory=EncouragementRules)


class OutputFormat(BaseModel):
    """输出结构定义(仅供文档说明，实际由代码控制返回)"""
    model_config = ConfigDict(extra="forbid")
    learningHighlights: list[str] = Field(...)
    nextWeekSuggestions: list[str] = Field(...)
    studentProgress: str = Field(..., description="面向家长的学生进步与优秀表现反馈")
    warmTips: str = Field(..., description="面向家长的温馨陪伴建议")
    encouragementMessage: str = Field(...)

    @field_validator("learningHighlights")
    @classmethod
    def validate_learning_highlights(cls, value: list[str], info: ValidationInfo) -> list[str]:
        if not value:
            raise ValueError("learningHighlights 不能为空")
        if any(not item.strip() for item in value):
            raise ValueError("learningHighlights 必须全部为非空字符串")

        context = info.context or {}
        rules = context.get("rules")
        metrics = context.get("metrics")
        if rules is not None:
            if len(value) < rules.highlightsMinCount:
                raise ValueError(f"learningHighlights 数量不足: {len(value)} < {rules.highlightsMinCount}")
            prefix = rules.highlightMustPrefix
            invalid_indexes = [str(index) for index, item in enumerate(value, start=1) if not item.startswith(prefix)]
            if invalid_indexes:
                raise ValueError(f"learningHighlights 第{','.join(invalid_indexes)}条未以 {prefix} 开头")

        if metrics is not None:
            task_completion_rate = metrics.weeklyTaskCompletionRatePct
            if task_completion_rate is not None and task_completion_rate >= 50:
                if not any("任务完成率" in item for item in value):
                    raise ValueError("learningHighlights 未体现本周任务完成率达标")
        return value

    @field_validator("nextWeekSuggestions")
    @classmethod
    def validate_next_week_suggestions(cls, value: list[str], info: ValidationInfo) -> list[str]:
        if not value:
            raise ValueError("nextWeekSuggestions 不能为空")
        if any(not item.strip() for item in value):
            raise ValueError("nextWeekSuggestions 必须全部为非空字符串")

        context = info.context or {}
        rules = context.get("rules")
        if rules is not None and len(value) != rules.suggestionsCount:
            raise ValueError(f"nextWeekSuggestions 数量错误: {len(value)} != {rules.suggestionsCount}")
        return value

    @field_validator("studentProgress")
    @classmethod
    def validate_student_progress(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("studentProgress 不能为空")
        return value

    @field_validator("warmTips")
    @classmethod
    def validate_warm_tips(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("warmTips 不能为空")
        return value

    @field_validator("encouragementMessage")
    @classmethod
    def validate_encouragement_message(cls, value: str, info: ValidationInfo) -> str:
        if not value.strip():
            raise ValueError("encouragementMessage 不能为空")

        context = info.context or {}
        rules = context.get("rules")
        student_name = context.get("student_name")

        if rules is not None:
            if rules.encouragementMustInclude.name and student_name and student_name not in value:
                raise ValueError("encouragementMessage 未包含学生姓名")

            affirm_words = rules.encouragementMustInclude.affirmWordsAnyOf
            if affirm_words and not any(word in value for word in affirm_words):
                raise ValueError("encouragementMessage 未包含指定肯定词")

            future_words = rules.encouragementMustInclude.futureWordsAnyOf
            if future_words and not any(word in value for word in future_words):
                raise ValueError("encouragementMessage 未包含指定未来词")

            if not value.endswith("🚀"):
                raise ValueError("encouragementMessage 末尾必须为 🚀")
        return value


class WeeklyReportRequest(BaseModel):
    """周报生成请求 - 完全对齐前端 JSON"""
    studentName: str = Field(..., description="学生姓名", examples=["Jinghang"])
    weekStart: str = Field(..., description="统计周开始日期(yyyy-MM-dd)", examples=["2026-05-18"])
    weekEnd: str = Field(..., description="统计周结束日期(yyyy-MM-dd)", examples=["2026-05-24"])
    metrics: Metrics = Field(..., description="核心指标")
    rules: Rules = Field(default_factory=Rules, description="文案生成约束")
    outputFormat: Optional[OutputFormat] = Field(None, description="输出结构定义(仅文档用)")


class WeeklyReportResponse(BaseModel):
    """周报生成响应 - 结构化返回"""
    success: bool = Field(..., description="是否成功")
    data: Optional[OutputFormat] = Field(None, description="结构化周报内容")
    error: Optional[str] = Field(None, description="错误信息")
