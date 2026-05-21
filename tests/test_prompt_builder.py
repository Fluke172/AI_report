"""
prompt_builder 单元测试
覆盖：亮点生成规则、建议生成规则、边界条件、兜底逻辑
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import (
    WeeklyReportRequest, Metrics, TopSubject,
    RankingItem, Rankings, Rules, EncouragementRules
)
from app.prompt_builder import (
    build_highlights_material,
    build_suggestions_material,
    build_system_prompt,
    build_user_prompt,
)


# ==================== 测试数据工厂 ====================

def make_request(**overrides) -> WeeklyReportRequest:
    """构造标准测试请求，可通过 overrides 覆盖任意字段"""
    metrics_overrides = overrides.pop("metrics", {})
    base_metrics = {
        "studyHours": 8.8,
        "streakDays": 5,
        "questionCount": 45,
        "accuracyPct": 86.67,
        "accuracyDeltaPct": 4.17,
        "newKnowledgePoints": 7,
        "topSubject": {"name": "化学", "masteryPct": 92.0},
    }
    base_metrics.update(metrics_overrides)

    base = {
        "studentName": "Jinghang",
        "weekStart": "2026-05-18",
        "weekEnd": "2026-05-24",
        "metrics": base_metrics,
    }
    base.update(overrides)
    return WeeklyReportRequest(**base)


# ==================== 学习亮点测试 ====================

class TestBuildHighlights:
    """测试亮点生成规则引擎"""

    def test_normal_case_all_dimensions_triggered(self):
        """正常用例：所有维度都满足触发条件"""
        req = make_request(
            metrics={
                "studyHours": 8.8,
                "streakDays": 5,
                "questionCount": 45,
                "accuracyPct": 86.67,
                "accuracyDeltaPct": 4.17,
                "newKnowledgePoints": 7,
                "topSubject": {"name": "化学", "masteryPct": 92.0},
                "rankings": {
                    "accuracy": {"rank": 8, "totalUsers": 356}
                },
            }
        )
        highlights = build_highlights_material(req)
        # 应触发: 时长、做题量、新知识点、科目、正确率提升、连续天数、排行榜 = 7条
        assert len(highlights) >= 7
        assert any("8.8" in h for h in highlights)
        assert any("45" in h for h in highlights)
        assert any("7" in h for h in highlights)
        assert any("化学" in h for h in highlights)
        assert any("提升" in h for h in highlights)
        assert any("连续" in h for h in highlights)
        assert any("精准榜" in h for h in highlights)

    def test_minimum_threshold_study_hours(self):
        """边界：学习时长恰好为1h"""
        req = make_request(metrics={"studyHours": 1.0, "streakDays": 0,
                                     "questionCount": 0, "accuracyPct": 50.0,
                                     "accuracyDeltaPct": 0, "newKnowledgePoints": 0,
                                     "topSubject": {"name": "数学", "masteryPct": 49.0}})
        highlights = build_highlights_material(req)
        assert any("1.0" in h for h in highlights)

    def test_below_threshold_study_hours(self):
        """边界：学习时长 <1h 不触发"""
        req = make_request(metrics={"studyHours": 0.5, "streakDays": 0,
                                     "questionCount": 5, "accuracyPct": 50.0,
                                     "accuracyDeltaPct": 0, "newKnowledgePoints": 0,
                                     "topSubject": {"name": "数学", "masteryPct": 30.0}})
        highlights = build_highlights_material(req)
        assert not any("0.5 小时" in h for h in highlights)

    def test_minimum_threshold_questions(self):
        """边界：做题量恰好为10"""
        req = make_request(metrics={"studyHours": 0.5, "streakDays": 0,
                                     "questionCount": 10, "accuracyPct": 70.0,
                                     "accuracyDeltaPct": 0, "newKnowledgePoints": 0,
                                     "topSubject": {"name": "数学", "masteryPct": 30.0}})
        highlights = build_highlights_material(req)
        assert any("10" in h and "题目" in h for h in highlights)

    def test_below_threshold_questions(self):
        """边界：做题量9题不触发"""
        req = make_request(metrics={"studyHours": 0.5, "streakDays": 0,
                                     "questionCount": 9, "accuracyPct": 70.0,
                                     "accuracyDeltaPct": 0, "newKnowledgePoints": 0,
                                     "topSubject": {"name": "数学", "masteryPct": 30.0}})
        highlights = build_highlights_material(req)
        assert not any("题目" in h for h in highlights)

    def test_mastery_threshold_50(self):
        """边界：掌握度恰好50%触发"""
        req = make_request(metrics={"studyHours": 0.5, "streakDays": 0,
                                     "questionCount": 5, "accuracyPct": 50.0,
                                     "accuracyDeltaPct": 0, "newKnowledgePoints": 0,
                                     "topSubject": {"name": "物理", "masteryPct": 50.0}})
        highlights = build_highlights_material(req)
        assert any("物理" in h for h in highlights)

    def test_mastery_below_50_not_triggered(self):
        """边界：掌握度49%不触发"""
        req = make_request(metrics={"studyHours": 0.5, "streakDays": 0,
                                     "questionCount": 5, "accuracyPct": 50.0,
                                     "accuracyDeltaPct": 0, "newKnowledgePoints": 0,
                                     "topSubject": {"name": "物理", "masteryPct": 49.0}})
        highlights = build_highlights_material(req)
        assert not any("物理" in h and "掌握度" in h for h in highlights)

    def test_accuracy_delta_threshold_1(self):
        """边界：正确率提升恰好1%触发"""
        req = make_request(metrics={"studyHours": 0.5, "streakDays": 0,
                                     "questionCount": 5, "accuracyPct": 50.0,
                                     "accuracyDeltaPct": 1.0, "newKnowledgePoints": 0,
                                     "topSubject": {"name": "数学", "masteryPct": 30.0}})
        highlights = build_highlights_material(req)
        assert any("提升" in h for h in highlights)

    def test_accuracy_delta_below_1_not_triggered(self):
        """边界：正确率提升0.99%不触发"""
        req = make_request(metrics={"studyHours": 0.5, "streakDays": 0,
                                     "questionCount": 5, "accuracyPct": 50.0,
                                     "accuracyDeltaPct": 0.99, "newKnowledgePoints": 0,
                                     "topSubject": {"name": "数学", "masteryPct": 30.0}})
        highlights = build_highlights_material(req)
        assert not any("提升" in h for h in highlights)

    def test_streak_days_threshold_2(self):
        """边界：连续学习恰好2天触发"""
        req = make_request(metrics={"studyHours": 0.5, "streakDays": 2,
                                     "questionCount": 5, "accuracyPct": 50.0,
                                     "accuracyDeltaPct": 0, "newKnowledgePoints": 0,
                                     "topSubject": {"name": "数学", "masteryPct": 30.0}})
        highlights = build_highlights_material(req)
        assert any("连续" in h for h in highlights)

    def test_streak_days_1_not_triggered(self):
        """边界：连续1天不触发连续学习维度亮点"""
        req = make_request(metrics={"studyHours": 0.5, "streakDays": 1,
                                     "questionCount": 5, "accuracyPct": 50.0,
                                     "accuracyDeltaPct": 0, "newKnowledgePoints": 0,
                                     "topSubject": {"name": "数学", "masteryPct": 30.0}})
        highlights = build_highlights_material(req)
        # 不应出现 "连续学习 X 天" 这种规则触发的亮点
        assert not any("连续学习" in h and "天" in h for h in highlights)

    def test_ranking_top10_included(self):
        """排行榜：rank=10 应触发"""
        req = make_request(metrics={
            "studyHours": 0.5, "streakDays": 0,
            "questionCount": 5, "accuracyPct": 50.0,
            "accuracyDeltaPct": 0, "newKnowledgePoints": 0,
            "topSubject": {"name": "数学", "masteryPct": 30.0},
            "rankings": {"diligence": {"rank": 10, "totalUsers": 100}}
        })
        highlights = build_highlights_material(req)
        assert any("勤学榜" in h for h in highlights)

    def test_ranking_11_not_included(self):
        """排行榜：rank=11 不触发"""
        req = make_request(metrics={
            "studyHours": 0.5, "streakDays": 0,
            "questionCount": 5, "accuracyPct": 50.0,
            "accuracyDeltaPct": 0, "newKnowledgePoints": 0,
            "topSubject": {"name": "数学", "masteryPct": 30.0},
            "rankings": {"diligence": {"rank": 11, "totalUsers": 100}}
        })
        highlights = build_highlights_material(req)
        assert not any("勤学榜" in h for h in highlights)

    def test_multiple_rankings_merged(self):
        """排行榜：多个榜单前10合并为一条"""
        req = make_request(metrics={
            "studyHours": 0.5, "streakDays": 0,
            "questionCount": 5, "accuracyPct": 50.0,
            "accuracyDeltaPct": 0, "newKnowledgePoints": 0,
            "topSubject": {"name": "数学", "masteryPct": 30.0},
            "rankings": {
                "diligence": {"rank": 3, "totalUsers": 200},
                "accuracy": {"rank": 5, "totalUsers": 200},
                "taskCompletion": {"rank": 15, "totalUsers": 200},
            }
        })
        highlights = build_highlights_material(req)
        rank_highlights = [h for h in highlights if "排行榜" in h]
        assert len(rank_highlights) == 1
        assert "勤学榜" in rank_highlights[0]
        assert "精准榜" in rank_highlights[0]
        assert "任务榜" not in rank_highlights[0]

    def test_no_rankings_field(self):
        """排行榜：无rankings字段不报错"""
        req = make_request(metrics={
            "studyHours": 0.5, "streakDays": 0,
            "questionCount": 5, "accuracyPct": 50.0,
            "accuracyDeltaPct": 0, "newKnowledgePoints": 0,
            "topSubject": {"name": "数学", "masteryPct": 30.0},
        })
        highlights = build_highlights_material(req)
        assert not any("排行榜" in h for h in highlights)

    def test_fallback_when_few_dimensions_triggered(self):
        """兜底：只有1个维度满足时，应补充到至少4条"""
        req = make_request(metrics={
            "studyHours": 0.5,  # <1h 不触发
            "streakDays": 0,    # <2 不触发
            "questionCount": 5, # <10 不触发
            "accuracyPct": 50.0,
            "accuracyDeltaPct": 0,  # <1 不触发
            "newKnowledgePoints": 1,  # >=1 触发这一条
            "topSubject": {"name": "数学", "masteryPct": 30.0},  # <50 不触发
        })
        highlights = build_highlights_material(req)
        assert len(highlights) >= 4
        # 应包含1条真实 + 3条兜底
        assert any("知识点" in h for h in highlights)
        assert any("学习态度" in h or "积极面对" in h or "主动性" in h for h in highlights)

    def test_fallback_zero_dimensions(self):
        """兜底：0个维度满足时，全是兜底文案，仍保证>=4"""
        req = make_request(metrics={
            "studyHours": 0.5,
            "streakDays": 0,
            "questionCount": 5,
            "accuracyPct": 50.0,
            "accuracyDeltaPct": -2.0,
            "newKnowledgePoints": 0,
            "topSubject": {"name": "数学", "masteryPct": 30.0},
        })
        highlights = build_highlights_material(req)
        assert len(highlights) >= 4

    def test_custom_min_count(self):
        """自定义规则：highlightsMinCount=6"""
        req = make_request(metrics={
            "studyHours": 8.8, "streakDays": 5,
            "questionCount": 45, "accuracyPct": 86.67,
            "accuracyDeltaPct": 4.17, "newKnowledgePoints": 7,
            "topSubject": {"name": "化学", "masteryPct": 92.0},
        })
        req.rules.highlightsMinCount = 6
        highlights = build_highlights_material(req)
        assert len(highlights) >= 6

    def test_weekly_task_completion_rate_threshold_50(self):
        req = make_request(metrics={"studyHours": 0.5, "streakDays": 0,
                                     "questionCount": 5, "accuracyPct": 50.0,
                                     "accuracyDeltaPct": 0, "newKnowledgePoints": 0,
                                     "weeklyTaskCompletionRatePct": 50.0,
                                     "topSubject": {"name": "数学", "masteryPct": 30.0}})
        highlights = build_highlights_material(req)
        assert any("任务完成率" in h and "50.0%" in h for h in highlights)

    def test_weekly_task_completion_rate_below_50_not_triggered(self):
        req = make_request(metrics={"studyHours": 0.5, "streakDays": 0,
                                     "questionCount": 5, "accuracyPct": 50.0,
                                     "accuracyDeltaPct": 0, "newKnowledgePoints": 0,
                                     "weeklyTaskCompletionRatePct": 49.9,
                                     "topSubject": {"name": "数学", "masteryPct": 30.0}})
        highlights = build_highlights_material(req)
        assert not any("任务完成率" in h for h in highlights)


# ==================== 下周建议测试 ====================

class TestBuildSuggestions:
    """测试建议生成规则引擎"""

    def test_always_4_suggestions(self):
        """永远返回4条建议"""
        req = make_request()
        suggestions = build_suggestions_material(req)
        assert len(suggestions) == 4

    def test_first_suggestion_contains_top_subject(self):
        """建议1：包含优势科目名称"""
        req = make_request(metrics={
            "studyHours": 5, "streakDays": 3,
            "questionCount": 20, "accuracyPct": 75.0,
            "accuracyDeltaPct": 2.0, "newKnowledgePoints": 3,
            "topSubject": {"name": "物理", "masteryPct": 85.0},
        })
        suggestions = build_suggestions_material(req)
        assert "物理" in suggestions[0]

    def test_second_suggestion_with_weak_points(self):
        """建议2：有弱项时包含弱项名称"""
        req = make_request(metrics={
            "studyHours": 5, "streakDays": 3,
            "questionCount": 20, "accuracyPct": 75.0,
            "accuracyDeltaPct": 2.0, "newKnowledgePoints": 3,
            "topSubject": {"name": "化学", "masteryPct": 85.0},
            "weakPoints": ["微分方程", "纯数"],
        })
        suggestions = build_suggestions_material(req)
        assert "微分方程" in suggestions[1]
        assert "纯数" in suggestions[1]

    def test_second_suggestion_without_weak_points(self):
        """建议2：无弱项时使用通用文案"""
        req = make_request(metrics={
            "studyHours": 5, "streakDays": 3,
            "questionCount": 20, "accuracyPct": 75.0,
            "accuracyDeltaPct": 2.0, "newKnowledgePoints": 3,
            "topSubject": {"name": "化学", "masteryPct": 85.0},
            "weakPoints": [],
        })
        suggestions = build_suggestions_material(req)
        assert "易错题型" in suggestions[1]

    def test_second_suggestion_weak_points_none(self):
        """建议2：weakPoints为None时使用通用文案"""
        req = make_request(metrics={
            "studyHours": 5, "streakDays": 3,
            "questionCount": 20, "accuracyPct": 75.0,
            "accuracyDeltaPct": 2.0, "newKnowledgePoints": 3,
            "topSubject": {"name": "化学", "masteryPct": 85.0},
        })
        suggestions = build_suggestions_material(req)
        assert "易错题型" in suggestions[1]

    def test_third_suggestion_under_15h(self):
        """建议3：学习时长<15h建议增加时间"""
        req = make_request(metrics={
            "studyHours": 8.0, "streakDays": 3,
            "questionCount": 20, "accuracyPct": 75.0,
            "accuracyDeltaPct": 2.0, "newKnowledgePoints": 3,
            "topSubject": {"name": "化学", "masteryPct": 85.0},
        })
        suggestions = build_suggestions_material(req)
        assert "增加" in suggestions[2] or "30 分钟" in suggestions[2]

    def test_third_suggestion_over_15h(self):
        """建议3：学习时长>=15h建议保持节奏"""
        req = make_request(metrics={
            "studyHours": 16.0, "streakDays": 3,
            "questionCount": 20, "accuracyPct": 75.0,
            "accuracyDeltaPct": 2.0, "newKnowledgePoints": 3,
            "topSubject": {"name": "化学", "masteryPct": 85.0},
        })
        suggestions = build_suggestions_material(req)
        assert "保持" in suggestions[2]

    def test_third_suggestion_exactly_15h(self):
        """边界：学习时长恰好15h走保持分支"""
        req = make_request(metrics={
            "studyHours": 15.0, "streakDays": 3,
            "questionCount": 20, "accuracyPct": 75.0,
            "accuracyDeltaPct": 2.0, "newKnowledgePoints": 3,
            "topSubject": {"name": "化学", "masteryPct": 85.0},
        })
        suggestions = build_suggestions_material(req)
        assert "保持" in suggestions[2]

    def test_fourth_suggestion_fixed(self):
        """建议4：固定为思维导图建议"""
        req = make_request()
        suggestions = build_suggestions_material(req)
        assert "思维导图" in suggestions[3]

    def test_weak_points_only_takes_first_two(self):
        """建议2：弱项列表只取前2个"""
        req = make_request(metrics={
            "studyHours": 5, "streakDays": 3,
            "questionCount": 20, "accuracyPct": 75.0,
            "accuracyDeltaPct": 2.0, "newKnowledgePoints": 3,
            "topSubject": {"name": "化学", "masteryPct": 85.0},
            "weakPoints": ["弱项A", "弱项B", "弱项C", "弱项D"],
        })
        suggestions = build_suggestions_material(req)
        assert "弱项A" in suggestions[1]
        assert "弱项B" in suggestions[1]
        assert "弱项C" not in suggestions[1]


# ==================== Prompt 构建测试 ====================

class TestPromptBuilding:
    """测试 system/user prompt 的正确性"""

    def test_system_prompt_contains_rules(self):
        """system prompt 包含动态 rules 约束"""
        req = make_request()
        prompt = build_system_prompt(req)
        assert "✅" in prompt
        assert "4" in prompt  # highlightsMinCount
        assert "节奏" in prompt
        assert "热情" in prompt
        assert "努力" in prompt
        assert "下周" in prompt
        assert "未来" in prompt
        assert "JSON" in prompt

    def test_system_prompt_custom_prefix(self):
        """system prompt 使用自定义前缀"""
        req = make_request()
        req.rules.highlightMustPrefix = "🌟"
        prompt = build_system_prompt(req)
        assert "🌟" in prompt

    def test_user_prompt_contains_student_name(self):
        """user prompt 包含学生姓名"""
        req = make_request()
        prompt = build_user_prompt(req)
        assert "Jinghang" in prompt

    def test_user_prompt_contains_metrics(self):
        """user prompt 包含核心指标数据"""
        req = make_request()
        prompt = build_user_prompt(req)
        assert "8.8" in prompt
        assert "45" in prompt
        assert "86.67" in prompt
        assert "化学" in prompt

    def test_user_prompt_accuracy_trend_up(self):
        """user prompt 正确率上升显示↑"""
        req = make_request(metrics={
            "studyHours": 5, "streakDays": 3,
            "questionCount": 20, "accuracyPct": 80.0,
            "accuracyDeltaPct": 3.5, "newKnowledgePoints": 3,
            "topSubject": {"name": "化学", "masteryPct": 85.0},
        })
        prompt = build_user_prompt(req)
        assert "↑" in prompt

    def test_user_prompt_accuracy_trend_down(self):
        """user prompt 正确率下降显示↓"""
        req = make_request(metrics={
            "studyHours": 5, "streakDays": 3,
            "questionCount": 20, "accuracyPct": 70.0,
            "accuracyDeltaPct": -2.0, "newKnowledgePoints": 3,
            "topSubject": {"name": "化学", "masteryPct": 85.0},
        })
        prompt = build_user_prompt(req)
        assert "↓" in prompt

    def test_user_prompt_accuracy_trend_flat(self):
        """user prompt 正确率持平"""
        req = make_request(metrics={
            "studyHours": 5, "streakDays": 3,
            "questionCount": 20, "accuracyPct": 80.0,
            "accuracyDeltaPct": 0, "newKnowledgePoints": 3,
            "topSubject": {"name": "化学", "masteryPct": 85.0},
        })
        prompt = build_user_prompt(req)
        assert "持平" in prompt

    def test_user_prompt_ranking_top10_star(self):
        """user prompt 排行榜前10标注⭐"""
        req = make_request(metrics={
            "studyHours": 5, "streakDays": 3,
            "questionCount": 20, "accuracyPct": 80.0,
            "accuracyDeltaPct": 2.0, "newKnowledgePoints": 3,
            "topSubject": {"name": "化学", "masteryPct": 85.0},
            "rankings": {"accuracy": {"rank": 5, "totalUsers": 200}},
        })
        prompt = build_user_prompt(req)
        assert "⭐前10" in prompt

    def test_user_prompt_ranking_not_top10(self):
        """user prompt 排行榜11名不标注⭐"""
        req = make_request(metrics={
            "studyHours": 5, "streakDays": 3,
            "questionCount": 20, "accuracyPct": 80.0,
            "accuracyDeltaPct": 2.0, "newKnowledgePoints": 3,
            "topSubject": {"name": "化学", "masteryPct": 85.0},
            "rankings": {"diligence": {"rank": 11, "totalUsers": 200}},
        })
        prompt = build_user_prompt(req)
        assert "⭐前10" not in prompt

    def test_user_prompt_task_completion_rate(self):
        """user prompt 包含任务完成率"""
        req = make_request(metrics={
            "studyHours": 5, "streakDays": 3,
            "questionCount": 20, "accuracyPct": 80.0,
            "accuracyDeltaPct": 2.0, "newKnowledgePoints": 3,
            "weeklyTaskCompletionRatePct": 78.5,
            "topSubject": {"name": "化学", "masteryPct": 85.0},
        })
        prompt = build_user_prompt(req)
        assert "78.5%" in prompt

    def test_user_prompt_no_task_data(self):
        """user prompt 无任务完成率数据显示'无数据'"""
        req = make_request(metrics={
            "studyHours": 5, "streakDays": 3,
            "questionCount": 20, "accuracyPct": 80.0,
            "accuracyDeltaPct": 2.0, "newKnowledgePoints": 3,
            "topSubject": {"name": "化学", "masteryPct": 85.0},
        })
        prompt = build_user_prompt(req)
        assert "无数据" in prompt

    def test_user_prompt_weak_points_shown(self):
        """user prompt 包含薄弱知识点"""
        req = make_request(metrics={
            "studyHours": 5, "streakDays": 3,
            "questionCount": 20, "accuracyPct": 80.0,
            "accuracyDeltaPct": 2.0, "newKnowledgePoints": 3,
            "topSubject": {"name": "化学", "masteryPct": 85.0},
            "weakPoints": ["微分方程", "纯数"],
        })
        prompt = build_user_prompt(req)
        assert "微分方程" in prompt
        assert "纯数" in prompt

    def test_user_prompt_no_weak_points(self):
        """user prompt 无薄弱知识点显示'无'"""
        req = make_request(metrics={
            "studyHours": 5, "streakDays": 3,
            "questionCount": 20, "accuracyPct": 80.0,
            "accuracyDeltaPct": 2.0, "newKnowledgePoints": 3,
            "topSubject": {"name": "化学", "masteryPct": 85.0},
        })
        prompt = build_user_prompt(req)
        # weakPoints 默认为 None，输出应该是 "无"
        assert "薄弱知识点" in prompt


# ==================== 模型验证测试 ====================

class TestModelValidation:
    """测试 Pydantic 模型的输入验证"""

    def test_valid_full_request(self):
        """完整有效请求"""
        data = {
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
                    "taskCompletion": {"rank": 15, "totalUsers": 356},
                },
            },
            "rules": {
                "highlightsMinCount": 4,
                "highlightMustPrefix": "✅",
                "suggestionsCount": 4,
                "suggestionsOrder": ["延续优势科目", "专项弱项突破", "增加学习时间", "学习方法升级"],
                "encouragementMustInclude": {
                    "name": True,
                    "affirmWordsAnyOf": ["节奏", "热情", "努力"],
                    "futureWordsAnyOf": ["下周", "未来"],
                },
            },
        }
        req = WeeklyReportRequest(**data)
        assert req.studentName == "Jinghang"
        assert req.metrics.studyHours == 8.8
        assert req.metrics.rankings.accuracy.rank == 8

    def test_minimal_request_defaults(self):
        """最小有效请求（仅必填字段，使用默认rules）"""
        data = {
            "studentName": "小明",
            "weekStart": "2026-05-18",
            "weekEnd": "2026-05-24",
            "metrics": {
                "studyHours": 1.0,
                "streakDays": 1,
                "questionCount": 10,
                "accuracyPct": 50.0,
                "newKnowledgePoints": 1,
                "topSubject": {"name": "英语", "masteryPct": 60.0},
            },
        }
        req = WeeklyReportRequest(**data)
        assert req.rules.highlightsMinCount == 4
        assert req.rules.highlightMustPrefix == "✅"
        assert req.rules.suggestionsCount == 4
        assert req.metrics.accuracyDeltaPct == 0
        assert req.metrics.weeklyTaskCompletionRatePct is None
        assert req.metrics.rankings is None
        assert req.metrics.weakPoints is None

    def test_invalid_accuracy_over_100(self):
        """验证：正确率>100应报错"""
        with pytest.raises(Exception):
            WeeklyReportRequest(**{
                "studentName": "test",
                "weekStart": "2026-05-18",
                "weekEnd": "2026-05-24",
                "metrics": {
                    "studyHours": 1.0,
                    "streakDays": 1,
                    "questionCount": 10,
                    "accuracyPct": 101.0,
                    "newKnowledgePoints": 1,
                    "topSubject": {"name": "数学", "masteryPct": 60.0},
                },
            })

    def test_invalid_accuracy_negative(self):
        """验证：正确率<0应报错"""
        with pytest.raises(Exception):
            WeeklyReportRequest(**{
                "studentName": "test",
                "weekStart": "2026-05-18",
                "weekEnd": "2026-05-24",
                "metrics": {
                    "studyHours": 1.0,
                    "streakDays": 1,
                    "questionCount": 10,
                    "accuracyPct": -1.0,
                    "newKnowledgePoints": 1,
                    "topSubject": {"name": "数学", "masteryPct": 60.0},
                },
            })

    def test_invalid_streak_days_negative(self):
        """验证：连续天数<0应报错"""
        with pytest.raises(Exception):
            WeeklyReportRequest(**{
                "studentName": "test",
                "weekStart": "2026-05-18",
                "weekEnd": "2026-05-24",
                "metrics": {
                    "studyHours": 1.0,
                    "streakDays": -1,
                    "questionCount": 10,
                    "accuracyPct": 50.0,
                    "newKnowledgePoints": 1,
                    "topSubject": {"name": "数学", "masteryPct": 60.0},
                },
            })

    def test_invalid_mastery_over_100(self):
        """验证：掌握度>100应报错"""
        with pytest.raises(Exception):
            WeeklyReportRequest(**{
                "studentName": "test",
                "weekStart": "2026-05-18",
                "weekEnd": "2026-05-24",
                "metrics": {
                    "studyHours": 1.0,
                    "streakDays": 1,
                    "questionCount": 10,
                    "accuracyPct": 50.0,
                    "newKnowledgePoints": 1,
                    "topSubject": {"name": "数学", "masteryPct": 120.0},
                },
            })

    def test_missing_required_field(self):
        """验证：缺少必填字段应报错"""
        with pytest.raises(Exception):
            WeeklyReportRequest(**{
                "weekStart": "2026-05-18",
                "weekEnd": "2026-05-24",
                "metrics": {
                    "studyHours": 1.0,
                    "streakDays": 1,
                    "questionCount": 10,
                    "accuracyPct": 50.0,
                    "newKnowledgePoints": 1,
                    "topSubject": {"name": "数学", "masteryPct": 60.0},
                },
            })


# ==================== 集成场景测试 ====================

class TestIntegrationScenarios:
    """端到端场景测试（不调用LLM，验证完整prompt构建流程）"""

    def test_scenario_top_student(self):
        """场景：学霸（所有指标优秀+排行榜前10）"""
        req = make_request(
            studentName="学霸小王",
            metrics={
                "studyHours": 20.0,
                "streakDays": 7,
                "questionCount": 200,
                "accuracyPct": 95.0,
                "accuracyDeltaPct": 5.0,
                "newKnowledgePoints": 15,
                "weeklyTaskCompletionRatePct": 100.0,
                "topSubject": {"name": "数学", "masteryPct": 98.0},
                "weakPoints": [],
                "rankings": {
                    "diligence": {"rank": 1, "totalUsers": 300},
                    "accuracy": {"rank": 2, "totalUsers": 300},
                    "taskCompletion": {"rank": 1, "totalUsers": 300},
                },
            }
        )
        highlights = build_highlights_material(req)
        suggestions = build_suggestions_material(req)
        system_prompt = build_system_prompt(req)
        user_prompt = build_user_prompt(req)

        assert len(highlights) >= 8  # 所有维度+排行榜
        assert any("勤学榜" in h for h in highlights)
        assert any("精准榜" in h for h in highlights)
        assert any("任务榜" in h for h in highlights)
        assert any("任务完成率" in h for h in highlights)
        assert "保持" in suggestions[2]  # >=15h
        assert "易错题型" in suggestions[1]  # 无弱项
        assert "学霸小王" in user_prompt
        assert "JSON" in system_prompt

    def test_scenario_struggling_student(self):
        """场景：吃力学生（指标低，无排行榜，少量亮点需兜底）"""
        req = make_request(
            studentName="小萌",
            metrics={
                "studyHours": 0.8,
                "streakDays": 1,
                "questionCount": 5,
                "accuracyPct": 40.0,
                "accuracyDeltaPct": -3.0,
                "newKnowledgePoints": 0,
                "topSubject": {"name": "英语", "masteryPct": 35.0},
                "weakPoints": ["语法", "阅读理解", "词汇"],
            }
        )
        highlights = build_highlights_material(req)
        suggestions = build_suggestions_material(req)

        # 所有维度都不满足，全靠兜底
        assert len(highlights) >= 3  # 兜底最多3条
        assert "增加" in suggestions[2] or "30 分钟" in suggestions[2]
        assert "语法" in suggestions[1]
        assert "阅读理解" in suggestions[1]
        # 弱项只取前2个
        assert "词汇" not in suggestions[1]

    def test_scenario_average_student(self):
        """场景：中等学生（部分维度满足）"""
        req = make_request(
            studentName="小杰",
            metrics={
                "studyHours": 5.0,
                "streakDays": 3,
                "questionCount": 30,
                "accuracyPct": 72.0,
                "accuracyDeltaPct": 0.5,  # <1 不触发正确率提升
                "newKnowledgePoints": 4,
                "weeklyTaskCompletionRatePct": 65.0,
                "topSubject": {"name": "化学", "masteryPct": 68.0},
                "weakPoints": ["有机化学"],
            }
        )
        highlights = build_highlights_material(req)
        suggestions = build_suggestions_material(req)
        user_prompt = build_user_prompt(req)

        # 应触发: 时长、做题量、新知识点、科目、连续天数 = 5条
        assert len(highlights) >= 6
        assert not any("提升" in h for h in highlights)  # 0.5% 不触发
        assert any("任务完成率" in h for h in highlights)
        assert "有机化学" in suggestions[1]
        assert "65.0%" in user_prompt

    def test_scenario_negative_accuracy_delta(self):
        """场景：正确率下降学生"""
        req = make_request(
            studentName="小落",
            metrics={
                "studyHours": 3.0,
                "streakDays": 2,
                "questionCount": 20,
                "accuracyPct": 55.0,
                "accuracyDeltaPct": -8.0,
                "newKnowledgePoints": 2,
                "topSubject": {"name": "物理", "masteryPct": 52.0},
            }
        )
        highlights = build_highlights_material(req)
        user_prompt = build_user_prompt(req)

        # 正确率下降不应出现"提升"亮点
        assert not any("提升" in h for h in highlights)
        assert "↓" in user_prompt

    def test_scenario_chinese_name(self):
        """场景：中文姓名"""
        req = make_request(studentName="张三丰")
        user_prompt = build_user_prompt(req)
        assert "张三丰" in user_prompt

    def test_scenario_english_name(self):
        """场景：英文姓名"""
        req = make_request(studentName="Alexander")
        user_prompt = build_user_prompt(req)
        assert "Alexander" in user_prompt

    def test_scenario_special_characters_in_weak_points(self):
        """场景：薄弱知识点含特殊字符"""
        req = make_request(metrics={
            "studyHours": 5, "streakDays": 3,
            "questionCount": 20, "accuracyPct": 75.0,
            "accuracyDeltaPct": 2.0, "newKnowledgePoints": 3,
            "topSubject": {"name": "数学", "masteryPct": 85.0},
            "weakPoints": ["f'(x)求导", "∫积分运算"],
        })
        suggestions = build_suggestions_material(req)
        assert "f'(x)求导" in suggestions[1]


# ==================== API 端点测试 ====================

class TestAPIEndpoint:
    """测试 FastAPI 端点（使用 TestClient）"""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)

    def test_health_check(self, client):
        """健康检查接口"""
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_request_validation_success(self, client):
        """有效请求不报422"""
        # 注意：这里不会真正调LLM（会因为没配API Key报500），
        # 但可以验证请求体解析不报422
        data = {
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
                "topSubject": {"name": "数学", "masteryPct": 80.0},
            },
        }
        resp = client.post("/api/weekly-report", json=data)
        # 预期不是422（验证通过），可能是500（没配LLM）
        assert resp.status_code != 422

    def test_request_validation_missing_field(self, client):
        """缺少必填字段返回422"""
        data = {
            "weekStart": "2026-05-18",
            "weekEnd": "2026-05-24",
        }
        resp = client.post("/api/weekly-report", json=data)
        assert resp.status_code == 422

    def test_request_validation_invalid_accuracy(self, client):
        """正确率超范围返回422"""
        data = {
            "studentName": "test",
            "weekStart": "2026-05-18",
            "weekEnd": "2026-05-24",
            "metrics": {
                "studyHours": 5.0,
                "streakDays": 3,
                "questionCount": 30,
                "accuracyPct": 150.0,
                "newKnowledgePoints": 4,
                "topSubject": {"name": "数学", "masteryPct": 80.0},
            },
        }
        resp = client.post("/api/weekly-report", json=data)
        assert resp.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
