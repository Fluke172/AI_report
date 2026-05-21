"""
详细输出测试 - 打印每个场景的完整 prompt 和规则引擎输出
直接运行: python tests/test_verbose.py
"""
import sys
import os
import json
import io

# 解决 Windows 终端 GBK 编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import WeeklyReportRequest
from app.prompt_builder import (
    build_highlights_material,
    build_suggestions_material,
    build_system_prompt,
    build_user_prompt,
)


def print_separator(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def print_subsection(title: str):
    print(f"\n  --- {title} ---")


def run_scenario(name: str, data: dict):
    """运行一个场景并打印完整输出"""
    print_separator(f"场景: {name}")

    # 解析请求
    req = WeeklyReportRequest(**data)
    print_subsection("输入数据")
    print(f"  学生: {req.studentName}")
    print(f"  周期: {req.weekStart} ~ {req.weekEnd}")
    m = req.metrics
    print(f"  学习时长: {m.studyHours}h")
    print(f"  连续天数: {m.streakDays}天")
    print(f"  做题量: {m.questionCount}道")
    print(f"  正确率: {m.accuracyPct}% (变化: {m.accuracyDeltaPct:+.2f}%)")
    print(f"  新知识点: {m.newKnowledgePoints}个")
    print(f"  任务完成率: {m.weeklyTaskCompletionRatePct}%"
          if m.weeklyTaskCompletionRatePct else "  任务完成率: 无数据")
    print(f"  优势科目: {m.topSubject.name} ({m.topSubject.masteryPct}%)")
    print(f"  薄弱知识点: {m.weakPoints or '无'}")
    if m.rankings:
        r = m.rankings
        parts = []
        if r.diligence:
            parts.append(f"勤学榜#{r.diligence.rank}/{r.diligence.totalUsers}")
        if r.accuracy:
            parts.append(f"精准榜#{r.accuracy.rank}/{r.accuracy.totalUsers}")
        if r.taskCompletion:
            parts.append(f"任务榜#{r.taskCompletion.rank}/{r.taskCompletion.totalUsers}")
        print(f"  排行榜: {', '.join(parts)}")
    else:
        print(f"  排行榜: 无数据")

    # 规则引擎输出
    print_subsection("规则引擎 → 学习亮点素材")
    highlights = build_highlights_material(req)
    for i, h in enumerate(highlights, 1):
        print(f"    [{i}] {h}")
    print(f"  总计: {len(highlights)} 条 (要求≥{req.rules.highlightsMinCount})")

    print_subsection("规则引擎 → 下周建议素材")
    suggestions = build_suggestions_material(req)
    for i, s in enumerate(suggestions, 1):
        print(f"    [{i}] {s}")
    print(f"  总计: {len(suggestions)} 条 (要求={req.rules.suggestionsCount})")

    # Prompt 输出
    print_subsection("System Prompt (前200字)")
    sp = build_system_prompt(req)
    print(f"    {sp[:200]}...")
    print(f"  System Prompt 总长度: {len(sp)} 字符")

    print_subsection("User Prompt (前500字)")
    up = build_user_prompt(req)
    print(f"    {up[:500]}...")
    print(f"  User Prompt 总长度: {len(up)} 字符")

    # 验证断言
    print_subsection("验证结果")
    errors = []
    if len(highlights) < req.rules.highlightsMinCount:
        errors.append(f"亮点数量不足: {len(highlights)} < {req.rules.highlightsMinCount}")
    if len(suggestions) != req.rules.suggestionsCount:
        errors.append(f"建议数量错误: {len(suggestions)} != {req.rules.suggestionsCount}")
    if req.studentName not in up:
        errors.append(f"User Prompt 未包含学生姓名")
    if "JSON" not in sp:
        errors.append(f"System Prompt 未要求 JSON 输出")

    if errors:
        for e in errors:
            print(f"    ❌ {e}")
    else:
        print(f"    ✅ 亮点数量合规 ({len(highlights)} ≥ {req.rules.highlightsMinCount})")
        print(f"    ✅ 建议数量合规 ({len(suggestions)} = {req.rules.suggestionsCount})")
        print(f"    ✅ User Prompt 包含学生姓名")
        print(f"    ✅ System Prompt 要求 JSON 输出")

    return len(errors) == 0


# ==================== 测试场景定义 ====================

SCENARIOS = {
    "1. 标准用例(你的实际输入)": {
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
    },
    "2. 学霸场景(全满分+全榜前3)": {
        "studentName": "学霸小王",
        "weekStart": "2026-05-18",
        "weekEnd": "2026-05-24",
        "metrics": {
            "studyHours": 22.5,
            "streakDays": 7,
            "questionCount": 300,
            "accuracyPct": 96.5,
            "accuracyDeltaPct": 6.0,
            "newKnowledgePoints": 20,
            "weeklyTaskCompletionRatePct": 100.0,
            "topSubject": {"name": "数学", "masteryPct": 99.0},
            "weakPoints": [],
            "rankings": {
                "diligence": {"rank": 1, "totalUsers": 400},
                "accuracy": {"rank": 2, "totalUsers": 400},
                "taskCompletion": {"rank": 1, "totalUsers": 400},
            },
        },
    },
    "3. 吃力学生(所有指标低于触发线)": {
        "studentName": "小萌",
        "weekStart": "2026-05-18",
        "weekEnd": "2026-05-24",
        "metrics": {
            "studyHours": 0.5,
            "streakDays": 1,
            "questionCount": 3,
            "accuracyPct": 35.0,
            "accuracyDeltaPct": -5.0,
            "newKnowledgePoints": 0,
            "topSubject": {"name": "英语", "masteryPct": 28.0},
            "weakPoints": ["语法", "阅读理解", "写作"],
        },
    },
    "4. 边界值(所有阈值恰好触发)": {
        "studentName": "边界测试",
        "weekStart": "2026-01-01",
        "weekEnd": "2026-01-07",
        "metrics": {
            "studyHours": 1.0,       # 恰好=1
            "streakDays": 2,         # 恰好=2
            "questionCount": 10,     # 恰好=10
            "accuracyPct": 60.0,
            "accuracyDeltaPct": 1.0, # 恰好=1
            "newKnowledgePoints": 1, # 恰好=1
            "topSubject": {"name": "物理", "masteryPct": 50.0},  # 恰好=50
            "rankings": {
                "accuracy": {"rank": 10, "totalUsers": 100},  # 恰好=10
            },
        },
    },
    "5. 边界值(所有阈值恰好不触发)": {
        "studentName": "边界测试B",
        "weekStart": "2026-01-01",
        "weekEnd": "2026-01-07",
        "metrics": {
            "studyHours": 0.99,
            "streakDays": 1,
            "questionCount": 9,
            "accuracyPct": 60.0,
            "accuracyDeltaPct": 0.99,
            "newKnowledgePoints": 0,
            "topSubject": {"name": "物理", "masteryPct": 49.9},
            "rankings": {
                "accuracy": {"rank": 11, "totalUsers": 100},
            },
        },
    },
    "6. 无可选字段(最小输入)": {
        "studentName": "最小输入",
        "weekStart": "2026-05-18",
        "weekEnd": "2026-05-24",
        "metrics": {
            "studyHours": 2.0,
            "streakDays": 0,
            "questionCount": 15,
            "accuracyPct": 70.0,
            "accuracyDeltaPct": 0,
            "newKnowledgePoints": 2,
            "topSubject": {"name": "数学", "masteryPct": 55.0},
        },
    },
    "7. 学习时长>=15h(走保持分支)": {
        "studentName": "勤奋同学",
        "weekStart": "2026-05-18",
        "weekEnd": "2026-05-24",
        "metrics": {
            "studyHours": 18.0,
            "streakDays": 6,
            "questionCount": 120,
            "accuracyPct": 78.0,
            "accuracyDeltaPct": 2.0,
            "newKnowledgePoints": 10,
            "topSubject": {"name": "经济", "masteryPct": 75.0},
            "weakPoints": ["宏观经济学"],
        },
    },
    "8. 正确率下降场景": {
        "studentName": "小落",
        "weekStart": "2026-05-18",
        "weekEnd": "2026-05-24",
        "metrics": {
            "studyHours": 6.0,
            "streakDays": 3,
            "questionCount": 40,
            "accuracyPct": 55.0,
            "accuracyDeltaPct": -12.0,
            "newKnowledgePoints": 3,
            "topSubject": {"name": "化学", "masteryPct": 60.0},
            "weakPoints": ["有机反应方程式", "化学平衡"],
        },
    },
}


# ==================== 主程序 ====================

if __name__ == "__main__":
    print("\n" + "█" * 70)
    print("  AI 学习周报 - 详细测试报告")
    print("  测试内容: 规则引擎 + Prompt 构建 + 数据验证")
    print("█" * 70)

    results = []
    for name, data in SCENARIOS.items():
        passed = run_scenario(name, data)
        results.append((name, passed))

    # 汇总
    print("\n\n" + "=" * 70)
    print("  测试汇总")
    print("=" * 70)
    total = len(results)
    passed_count = sum(1 for _, p in results if p)
    failed_count = total - passed_count

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}  {name}")

    print(f"\n  总计: {total} 个场景, {passed_count} 通过, {failed_count} 失败")

    if failed_count > 0:
        print("\n  ⚠️  有失败场景，请检查后再上线！")
        sys.exit(1)
    else:
        print("\n  🎉 全部通过，可以上线！")
        sys.exit(0)
