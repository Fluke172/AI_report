"""AI 学习周报生成服务"""

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from app.models import WeeklyReportRequest, WeeklyReportResponse
from app.prompt_builder import build_system_prompt, build_user_prompt
from app.llm_client import generate_report

load_dotenv()

app = FastAPI(
    title="AI 学习周报生成服务",
    description="输入学生每周学习数据，返回结构化的AI学习周报（学习亮点、下周建议、鼓励寄语）",
    version="2.0.0",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/weekly-report", response_model=WeeklyReportResponse)
def create_weekly_report(req: WeeklyReportRequest):
    """
    生成AI学习周报

    输入学生的每周学习数据和规则约束，返回结构化的周报内容：
    - learningHighlights: 学习亮点数组
    - nextWeekSuggestions: 下周建议数组
    - encouragementMessage: 鼓励寄语
    """
    try:
        system_prompt = build_system_prompt(req)
        user_prompt = build_user_prompt(req)
        report_data = generate_report(system_prompt, user_prompt, request=req)
        return WeeklyReportResponse(success=True, data=report_data)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        return WeeklyReportResponse(success=False, error=f"生成周报失败: {str(e)}")
