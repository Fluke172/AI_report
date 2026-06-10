"""豆包大模型（火山方舟）客户端 - 返回结构化 JSON"""

import json
import os
from typing import Optional
from openai import OpenAI
from app.models import OutputFormat, WeeklyReportRequest
from app.prompt_builder import (
    build_highlights_material,
    build_student_progress_material,
    build_suggestions_material,
    build_warm_tips_material,
)


def get_client() -> OpenAI:
    """获取火山方舟 OpenAI 兼容客户端"""
    api_key = os.getenv("ARK_API_KEY")
    base_url = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")

    if not api_key:
        raise ValueError("ARK_API_KEY 环境变量未设置")

    return OpenAI(api_key=api_key, base_url=base_url)


def extract_json_text(raw_text: str) -> str:
    """提取模型输出中的 JSON 文本"""
    cleaned_text = raw_text.strip()

    # 尝试提取 JSON（兼容模型可能包裹 ```json``` 的情况）
    if cleaned_text.startswith("```"):
        lines = cleaned_text.split("\n")
        json_lines = []
        in_block = False
        for line in lines:
            if line.strip().startswith("```"):
                in_block = not in_block
                continue
            if in_block or not line.strip().startswith("```"):
                json_lines.append(line)
        cleaned_text = "\n".join(json_lines).strip()

    return cleaned_text


def validate_report_payload(parsed: dict, request: Optional[WeeklyReportRequest] = None) -> OutputFormat:
    """使用 Pydantic 对模型输出做严格结构校验与业务校验"""
    context = None
    if request is not None:
        context = {
            "rules": request.rules,
            "metrics": request.metrics,
            "student_name": request.studentName,
        }
    return OutputFormat.model_validate(parsed, context=context)


def request_model_once(client: OpenAI, endpoint_id: str, system_prompt: str, user_prompt: str) -> str:
    response = client.chat.completions.create(
        model=endpoint_id,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=2000,
    )
    return response.choices[0].message.content.strip()


def build_retry_prompt(user_prompt: str, error_message: str) -> str:
    return (
        f"{user_prompt}\n\n"
        f"上一次输出未通过程序校验，原因：{error_message}\n"
        "请严格修正为可直接解析的合法 JSON，只输出 JSON，不要输出任何解释。"
    )


def build_fallback_report(request: WeeklyReportRequest) -> OutputFormat:
    rules = request.rules
    prefix = rules.highlightMustPrefix

    highlights = [
        item if item.startswith(prefix) else f"{prefix} {item}"
        for item in build_highlights_material(request)
    ]
    extra_highlights = [
        f"{prefix} 本周保持学习投入，基础积累正在稳步推进",
        f"{prefix} 愿意持续参与学习，本周的坚持值得肯定",
        f"{prefix} 学习状态总体稳定，正在逐步建立自信",
        f"{prefix} 能够围绕目标推进学习，执行力持续提升",
    ]
    extra_index = 0
    while len(highlights) < rules.highlightsMinCount:
        if extra_index < len(extra_highlights):
            highlights.append(extra_highlights[extra_index])
            extra_index += 1
        else:
            highlights.append(f"{prefix} 本周持续投入学习，第{len(highlights) + 1}项亮点表现稳定")

    suggestions = build_suggestions_material(request)
    extra_suggestions = [
        "继续通过错题复盘查漏补缺，提升知识掌握稳定性",
        "把每日学习任务拆小并按时完成，增强持续执行力",
        "每周安排一次阶段总结，及时调整复习重点",
        "结合课堂内容和练习反馈，优化自己的学习节奏",
    ]
    extra_index = 0
    while len(suggestions) < rules.suggestionsCount:
        if extra_index < len(extra_suggestions):
            suggestions.append(extra_suggestions[extra_index])
            extra_index += 1
        else:
            suggestions.append(f"围绕第{len(suggestions) + 1}个目标安排专项练习，逐步提升综合表现")
    suggestions = suggestions[:rules.suggestionsCount]

    affirm_word = rules.encouragementMustInclude.affirmWordsAnyOf[0] if rules.encouragementMustInclude.affirmWordsAnyOf else "努力"
    future_word = rules.encouragementMustInclude.futureWordsAnyOf[0] if rules.encouragementMustInclude.futureWordsAnyOf else "下周"
    encouragement_message = (
        f"{request.studentName}，这周你的{affirm_word}值得肯定，期待你{future_word}继续保持稳定节奏，"
        "一步一步看到更扎实的进步🚀"
    )
    progress_points = build_student_progress_material(request).split("；")
    if len(progress_points) == 1 and progress_points[0].startswith("本周能"):
        student_progress = (
            f"{request.studentName}本周能持续参与学习并面对练习任务，这份愿意尝试的状态值得肯定。"
        )
    else:
        progress_summary = "、".join(progress_points[:3])
        student_progress = (
            f"{request.studentName}本周在{progress_summary}方面表现积极，"
            "能看出孩子正在稳步积累信心和方法。"
        )
    warm_tips = build_warm_tips_material(request)

    payload = {
        "learningHighlights": highlights,
        "nextWeekSuggestions": suggestions,
        "studentProgress": student_progress,
        "warmTips": warm_tips,
        "encouragementMessage": encouragement_message,
    }
    return validate_report_payload(payload, request=request)


def generate_report(
    system_prompt: str,
    user_prompt: str,
    request: Optional[WeeklyReportRequest] = None,
) -> OutputFormat:
    """调用豆包模型生成周报，解析为结构化 OutputFormat"""
    client = get_client()
    endpoint_id = os.getenv("ARK_ENDPOINT_ID")

    if not endpoint_id:
        raise ValueError("ARK_ENDPOINT_ID 环境变量未设置")

    current_user_prompt = user_prompt
    last_error: Optional[Exception] = None

    for attempt in range(2):
        try:
            raw_text = request_model_once(client, endpoint_id, system_prompt, current_user_prompt)
            json_text = extract_json_text(raw_text)
            parsed = json.loads(json_text)
            return validate_report_payload(parsed, request=request)
        except Exception as exc:
            last_error = exc
            if request is None:
                raise
            if attempt == 0:
                current_user_prompt = build_retry_prompt(user_prompt, str(exc))
                continue

    if request is not None:
        return build_fallback_report(request)

    if last_error is not None:
        raise last_error
    raise RuntimeError("生成周报失败")
