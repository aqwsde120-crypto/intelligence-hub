"""주간 QA 브리핑 자동 생성"""

import os
import logging
from datetime import date, timedelta
import google.generativeai as genai
from app.database.supabase_client import get_client, upsert_weekly_briefing

logger = logging.getLogger(__name__)
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
_model = genai.GenerativeModel("gemini-1.5-pro")


def _get_week_start() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def generate() -> str:
    db = get_client()
    week_start = _get_week_start()
    week_end = week_start + timedelta(days=6)

    # 이번 주 데이터 수집
    wl = db.table("warning_letters").select("company_name,country,issued_date,ai_analyses(summary,risk_level,ckd_impact,recommended_action)").gte("issued_date", week_start.isoformat()).lte("issued_date", week_end.isoformat()).execute().data
    f483 = db.table("fda_483").select("company_name,inspection_date,ai_analyses(summary,risk_level,ckd_impact)").gte("inspection_date", week_start.isoformat()).lte("inspection_date", week_end.isoformat()).execute().data
    mfds = db.table("mfds_notices").select("title,published_date,ai_analyses(summary,ckd_impact,recommended_action)").gte("published_date", week_start.isoformat()).lte("published_date", week_end.isoformat()).execute().data

    def fmt_list(items, fields):
        if not items:
            return "해당 없음"
        lines = []
        for item in items[:5]:
            ai = item.get("ai_analyses") or {}
            if isinstance(ai, list):
                ai = ai[0] if ai else {}
            parts = [f"- {item.get(fields[0], 'N/A')}"]
            if ai.get("summary"):
                parts.append(f"  요약: {ai['summary'][:100]}")
            if ai.get("risk_level"):
                parts.append(f"  위험도: {ai['risk_level']}")
            lines.append("\n".join(parts))
        return "\n".join(lines)

    context = f"""
주간 기간: {week_start} ~ {week_end}

[신규 Warning Letter ({len(wl)}건)]
{fmt_list(wl, ['company_name'])}

[신규 FDA 483 ({len(f483)}건)]
{fmt_list(f483, ['company_name'])}

[MFDS 공지 ({len(mfds)}건)]
{fmt_list(mfds, ['title'])}
"""

    prompt = f"""당신은 종근당 QA 조직의 수석 전문가입니다.
아래 이번 주 QA 인텔리전스 데이터를 바탕으로, 경영진 보고 수준의 주간 QA 브리핑을 한국어로 작성하세요.

{context}

브리핑은 다음 섹션을 포함해야 합니다:
1. 이번 주 핵심 요약 (3줄 이내)
2. 주요 GMP 규제 변화
3. 신규 Warning Letter 분석
4. FDA 483 주요 지적사항
5. MFDS 공지 핵심 내용
6. 종근당 QA 권장 Action Items (번호 목록, 담당 부서 및 기한 포함)

전문적이고 간결하게 작성하며, 경영진이 5분 내에 핵심을 파악할 수 있도록 합니다.
"""
    try:
        resp = _model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(max_output_tokens=2000, temperature=0.2),
        )
        briefing = resp.text.strip()

        # Action Items 별도 추출
        action_prompt = f"위 브리핑에서 '종근당 QA 권장 Action Items' 섹션만 추출하여 그대로 반환하세요:\n{briefing}"
        action_resp = _model.generate_content(action_prompt)
        actions = action_resp.text.strip()

        upsert_weekly_briefing(week_start.isoformat(), briefing, actions)
        logger.info(f"주간 브리핑 생성 완료: {week_start}")
        return briefing
    except Exception as e:
        logger.error(f"브리핑 생성 실패: {e}")
        return f"브리핑 생성 실패: {e}"
