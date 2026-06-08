"""
Google Gemini AI 분석 모듈
"""

import os
import logging
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
_model = genai.GenerativeModel("gemini-1.5-pro")

SYSTEM_PREFIX = """당신은 종근당 QA 조직의 수석 GMP 전문가입니다.
글로벌 GMP 규정(FDA, EMA, PIC/S, ICH)에 정통하며, 한국 MFDS 규정도 깊이 이해합니다.
모든 분석은 반드시 한국어로 작성하며, 종근당의 사업 특성과 품질 위험을 중심으로 실용적인 인사이트를 제공합니다.
"""


def _call(prompt: str, max_tokens: int = 1500) -> str:
    try:
        resp = _model.generate_content(
            SYSTEM_PREFIX + "\n\n" + prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=0.2,
            ),
        )
        return resp.text.strip()
    except Exception as e:
        logger.error(f"Gemini API 오류: {e}")
        return f"[분석 오류: {e}]"


def analyze_warning_letter(record: dict) -> dict:
    prompt = f"""
다음 FDA Warning Letter를 종근당 QA 관점에서 심층 분석하세요.

업체명: {record.get('company_name')}
국가: {record.get('country')}
발행일: {record.get('issued_date')}
원문 내용:
{record.get('content', '')[:4000]}

아래 항목 각각에 대해 구체적으로 분석하세요. 각 항목은 "항목명:" 형식으로 시작하세요.

요약: (2~3문장 핵심 요약)
Root Cause: (근본 원인 분석)
GMP 위반 영역: (위반된 GMP 항목 명시)
예상 CAPA: (구체적 시정조치 방향)
Lessons Learned: (타 제약사 및 종근당 적용 교훈)
종근당 영향도: (High/Medium/Low 및 구체적 영향 설명)
권장 조치사항: (종근당 QA팀이 즉시 취해야 할 조치)
ALCOA 카테고리: (데이터 완전성 관련 여부 및 해당 ALCOA+ 항목, 해당 없으면 "해당없음")
위험도: (High/Medium/Low)
"""
    raw = _call(prompt)
    return _parse_analysis(raw, ["요약", "Root Cause", "GMP 위반 영역", "예상 CAPA",
                                  "Lessons Learned", "종근당 영향도", "권장 조치사항",
                                  "ALCOA 카테고리", "위험도"])


def analyze_fda_483(record: dict) -> dict:
    prompt = f"""
다음 FDA 483 Observation을 종근당 QA 관점에서 분석하세요.

업체명: {record.get('company_name')}
실사일: {record.get('inspection_date')}
Observation 내용:
{record.get('content', '')[:4000]}

아래 항목 각각에 대해 분석하세요. 각 항목은 "항목명:" 형식으로 시작하세요.

요약: (주요 Observation 2~3문장 요약)
GMP 카테고리: (해당 GMP 영역 분류)
반복 지적 여부: (반복 지적 가능성 및 근거)
품질 리스크: (예상 품질 위험)
종근당 영향도: (High/Medium/Low 및 설명)
권장 조치사항: (종근당 QA팀 대응 방향)
ALCOA 카테고리: (데이터 완전성 관련 여부)
위험도: (High/Medium/Low)
"""
    raw = _call(prompt)
    return _parse_analysis(raw, ["요약", "GMP 카테고리", "반복 지적 여부", "품질 리스크",
                                  "종근당 영향도", "권장 조치사항", "ALCOA 카테고리", "위험도"])


def analyze_mfds_notice(record: dict) -> dict:
    prompt = f"""
다음 MFDS(식품의약품안전처) 공지사항을 종근당 QA 관점에서 분석하세요.

제목: {record.get('title')}
공지일: {record.get('published_date')}
내용:
{record.get('content', '')[:4000]}

아래 항목 각각에 대해 분석하세요.

요약: (공지 핵심 2~3문장)
주요 변경사항: (구체적 변경 내용)
적용 대상: (해당 제품군/공정)
종근당 영향도: (High/Medium/Low 및 설명)
준비 필요사항: (종근당이 준비해야 할 사항)
위험도: (High/Medium/Low)
"""
    raw = _call(prompt)
    return _parse_analysis(raw, ["요약", "주요 변경사항", "적용 대상", "종근당 영향도",
                                  "준비 필요사항", "위험도"])


def _parse_analysis(text: str, keys: list[str]) -> dict:
    """AI 응답 텍스트를 구조화된 dict로 파싱"""
    result: dict[str, str] = {}
    lines = text.split("\n")
    current_key = None
    buffer: list[str] = []

    key_map = {
        "요약": "summary", "root cause": "root_cause", "gmp 위반 영역": "gmp_area",
        "gmp 카테고리": "gmp_area", "예상 capa": "capa", "lessons learned": "lessons_learned",
        "종근당 영향도": "ckd_impact", "권장 조치사항": "recommended_action",
        "alcoa 카테고리": "alcoa_category", "위험도": "risk_level",
        "반복 지적 여부": "root_cause", "품질 리스크": "lessons_learned",
        "주요 변경사항": "root_cause", "적용 대상": "gmp_area",
        "준비 필요사항": "recommended_action",
    }

    for line in lines:
        matched = False
        for k in keys:
            if line.lower().startswith(k.lower() + ":"):
                if current_key:
                    result[current_key] = "\n".join(buffer).strip()
                current_key = key_map.get(k.lower(), k.lower().replace(" ", "_"))
                buffer = [line[len(k) + 1:].strip()]
                matched = True
                break
        if not matched and current_key:
            buffer.append(line)

    if current_key:
        result[current_key] = "\n".join(buffer).strip()

    return result


def run_all_analyses() -> int:
    """미분석 항목 전체 분석 실행. 분석 완료 건수 반환."""
    from app.database.supabase_client import get_client, upsert_ai_analysis
    import time

    db = get_client()
    count = 0

    # Warning Letters
    wl_res = db.table("warning_letters").select("id,company_name,country,issued_date,content").execute()
    for row in wl_res.data:
        existing = db.table("ai_analyses").select("id").eq("source_type", "warning_letter").eq("source_id", row["id"]).execute()
        if existing.data:
            continue
        analysis = analyze_warning_letter(row)
        upsert_ai_analysis("warning_letter", row["id"], analysis)
        count += 1
        time.sleep(2)

    # FDA 483
    f483_res = db.table("fda_483").select("id,company_name,inspection_date,content").execute()
    for row in f483_res.data:
        existing = db.table("ai_analyses").select("id").eq("source_type", "fda_483").eq("source_id", row["id"]).execute()
        if existing.data:
            continue
        analysis = analyze_fda_483(row)
        upsert_ai_analysis("fda_483", row["id"], analysis)
        count += 1
        time.sleep(2)

    # MFDS
    mfds_res = db.table("mfds_notices").select("id,title,published_date,content").execute()
    for row in mfds_res.data:
        existing = db.table("ai_analyses").select("id").eq("source_type", "mfds_notice").eq("source_id", row["id"]).execute()
        if existing.data:
            continue
        analysis = analyze_mfds_notice(row)
        upsert_ai_analysis("mfds_notice", row["id"], analysis)
        count += 1
        time.sleep(2)

    return count
