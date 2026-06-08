# 종근당 QA Intelligence Hub — 전체 프로젝트

## 프로젝트 구조

```
ckd-qa-hub/
├── .github/workflows/weekly_collect.yml
├── .streamlit/config.toml
├── app/
│   ├── collectors/
│   │   ├── fda_warning_letters.py
│   │   ├── fda_483.py
│   │   └── mfds_notices.py
│   ├── ai/
│   │   ├── gemini_analyzer.py
│   │   └── weekly_briefing.py
│   ├── database/
│   │   ├── supabase_client.py
│   │   └── schema.sql
│   ├── pages/
│   │   ├── 1_대시보드.py
│   │   ├── 2_GMP_규제동향.py
│   │   ├── 3_Warning_Letter.py
│   │   ├── 4_FDA_483.py
│   │   └── 5_데이터완전성.py
│   └── utils/
│       ├── charts.py
│       └── export.py
├── scripts/run_weekly.py
├── Home.py
├── requirements.txt
└── .env.example
```

---

## requirements.txt

```txt
streamlit==1.32.0
supabase==2.3.4
google-generativeai==0.4.1
requests==2.31.0
beautifulsoup4==4.12.3
pandas==2.2.1
plotly==5.20.0
openpyxl==3.1.2
python-dotenv==1.0.1
lxml==5.1.0
httpx==0.27.0
kaleido==0.2.1
```

---

## .env.example

```env
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_KEY=your_supabase_anon_key
GEMINI_API_KEY=your_gemini_api_key
```

---

## .streamlit/config.toml

```toml
[theme]
primaryColor = "#005BAC"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F4F8"
textColor = "#1A1A2E"
font = "sans serif"

[server]
maxUploadSize = 50

[browser]
gatherUsageStats = false
```

---

## app/database/schema.sql

```sql
-- Warning Letters
CREATE TABLE IF NOT EXISTS warning_letters (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    company_name TEXT NOT NULL,
    country TEXT,
    issued_date DATE,
    source_url TEXT UNIQUE NOT NULL,
    content TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- FDA 483
CREATE TABLE IF NOT EXISTS fda_483 (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    company_name TEXT NOT NULL,
    inspection_date DATE,
    source_url TEXT UNIQUE NOT NULL,
    content TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- MFDS 공지사항
CREATE TABLE IF NOT EXISTS mfds_notices (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    title TEXT NOT NULL,
    published_date DATE,
    source_url TEXT UNIQUE NOT NULL,
    content TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- AI 분석 결과
CREATE TABLE IF NOT EXISTS ai_analyses (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    source_type TEXT NOT NULL,  -- 'warning_letter' | 'fda_483' | 'mfds_notice'
    source_id UUID NOT NULL,
    summary TEXT,
    root_cause TEXT,
    gmp_area TEXT,
    risk_level TEXT,
    capa TEXT,
    lessons_learned TEXT,
    ckd_impact TEXT,
    recommended_action TEXT,
    alcoa_category TEXT,        -- 데이터 완전성 분류
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_type, source_id)
);

-- 주간 브리핑
CREATE TABLE IF NOT EXISTS weekly_briefings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    week_start DATE NOT NULL UNIQUE,
    briefing_content TEXT,
    action_items TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS 정책
ALTER TABLE warning_letters ENABLE ROW LEVEL SECURITY;
ALTER TABLE fda_483 ENABLE ROW LEVEL SECURITY;
ALTER TABLE mfds_notices ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_briefings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "allow_all" ON warning_letters FOR ALL USING (true);
CREATE POLICY "allow_all" ON fda_483 FOR ALL USING (true);
CREATE POLICY "allow_all" ON mfds_notices FOR ALL USING (true);
CREATE POLICY "allow_all" ON ai_analyses FOR ALL USING (true);
CREATE POLICY "allow_all" ON weekly_briefings FOR ALL USING (true);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_wl_date ON warning_letters(issued_date DESC);
CREATE INDEX IF NOT EXISTS idx_483_date ON fda_483(inspection_date DESC);
CREATE INDEX IF NOT EXISTS idx_mfds_date ON mfds_notices(published_date DESC);
CREATE INDEX IF NOT EXISTS idx_ai_source ON ai_analyses(source_type, source_id);
```

---

## app/database/supabase_client.py

```python
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_KEY"]
        _client = create_client(url, key)
    return _client


def fetch_warning_letters(limit: int = 100, offset: int = 0) -> list[dict]:
    db = get_client()
    res = (
        db.table("warning_letters")
        .select("*, ai_analyses(*)")
        .order("issued_date", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return res.data


def fetch_fda_483(limit: int = 100, offset: int = 0) -> list[dict]:
    db = get_client()
    res = (
        db.table("fda_483")
        .select("*, ai_analyses(*)")
        .order("inspection_date", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return res.data


def fetch_mfds_notices(limit: int = 100) -> list[dict]:
    db = get_client()
    res = (
        db.table("mfds_notices")
        .select("*, ai_analyses(*)")
        .order("published_date", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data


def fetch_weekly_briefing(week_start: str) -> dict | None:
    db = get_client()
    res = (
        db.table("weekly_briefings")
        .select("*")
        .eq("week_start", week_start)
        .maybe_single()
        .execute()
    )
    return res.data


def upsert_ai_analysis(source_type: str, source_id: str, analysis: dict) -> None:
    db = get_client()
    db.table("ai_analyses").upsert(
        {"source_type": source_type, "source_id": source_id, **analysis},
        on_conflict="source_type,source_id",
    ).execute()


def upsert_weekly_briefing(week_start: str, content: str, actions: str) -> None:
    db = get_client()
    db.table("weekly_briefings").upsert(
        {"week_start": week_start, "briefing_content": content, "action_items": actions},
        on_conflict="week_start",
    ).execute()


def count_new_this_week(table: str, date_col: str) -> int:
    """이번 주(월요일~오늘) 신규 건수 반환"""
    from datetime import date, timedelta
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    db = get_client()
    res = (
        db.table(table)
        .select("id", count="exact")
        .gte(date_col, monday.isoformat())
        .execute()
    )
    return res.count or 0
```

---

## app/collectors/fda_warning_letters.py

```python
"""
FDA Warning Letter 수집기
출처: https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/
      compliance-actions-and-activities/warning-letters
"""

import time
import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from app.database.supabase_client import get_client

logger = logging.getLogger(__name__)

BASE_URL = "https://www.fda.gov"
LIST_URL = (
    "https://www.fda.gov/inspections-compliance-enforcement-and-criminal-"
    "investigations/compliance-actions-and-activities/warning-letters"
)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; CKD-QA-Hub/1.0; +https://github.com/ckd-qa)"
    )
}


def _parse_date(text: str) -> str | None:
    for fmt in ("%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _fetch_letter_content(url: str) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        main = soup.find("div", {"class": "lcds-text-field"}) or soup.find("main")
        return main.get_text(separator="\n", strip=True)[:8000] if main else ""
    except Exception as e:
        logger.warning(f"본문 수집 실패 {url}: {e}")
        return ""


def collect(max_pages: int = 3) -> int:
    """최근 max_pages 페이지 분의 Warning Letter 수집. 신규 저장 건수 반환."""
    db = get_client()
    saved = 0

    for page in range(max_pages):
        url = LIST_URL + (f"?page={page}" if page > 0 else "")
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
        except Exception as e:
            logger.error(f"목록 페이지 요청 실패 (page={page}): {e}")
            break

        soup = BeautifulSoup(r.text, "lxml")
        rows = soup.select("table.table tbody tr")
        if not rows:
            logger.info(f"page={page}: 행 없음, 수집 종료")
            break

        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue

            link_tag = cols[0].find("a")
            if not link_tag:
                continue

            company = link_tag.get_text(strip=True)
            href = link_tag.get("href", "")
            if href.startswith("/"):
                href = BASE_URL + href

            issued_date = _parse_date(cols[1].get_text())
            country = cols[2].get_text(strip=True) if len(cols) > 2 else None

            # 이미 존재하면 스킵
            existing = (
                db.table("warning_letters")
                .select("id")
                .eq("source_url", href)
                .execute()
            )
            if existing.data:
                continue

            content = _fetch_letter_content(href)
            record = {
                "company_name": company,
                "country": country,
                "issued_date": issued_date,
                "source_url": href,
                "content": content,
            }
            db.table("warning_letters").insert(record).execute()
            saved += 1
            logger.info(f"저장: {company} ({issued_date})")
            time.sleep(1.5)

    logger.info(f"Warning Letter 수집 완료: {saved}건 신규 저장")
    return saved
```

---

## app/collectors/fda_483.py

```python
"""
FDA 483 (Inspection Observations) 수집기
출처: https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/
      inspection-references/inspection-observations
"""

import time
import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from app.database.supabase_client import get_client

logger = logging.getLogger(__name__)

BASE_URL = "https://www.fda.gov"
LIST_URL = (
    "https://www.fda.gov/inspections-compliance-enforcement-and-criminal-"
    "investigations/inspection-references/inspection-observations"
)
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CKD-QA-Hub/1.0)"}


def _parse_date(text: str) -> str | None:
    for fmt in ("%m/%d/%Y", "%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _fetch_observation_content(url: str) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        main = soup.find("main") or soup.find("div", {"class": "lcds-text-field"})
        return main.get_text(separator="\n", strip=True)[:8000] if main else ""
    except Exception as e:
        logger.warning(f"본문 수집 실패 {url}: {e}")
        return ""


def collect(max_pages: int = 3) -> int:
    db = get_client()
    saved = 0

    for page in range(max_pages):
        url = LIST_URL + (f"?page={page}" if page > 0 else "")
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
        except Exception as e:
            logger.error(f"목록 요청 실패 (page={page}): {e}")
            break

        soup = BeautifulSoup(r.text, "lxml")
        rows = soup.select("table.table tbody tr")
        if not rows:
            break

        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 2:
                continue

            link_tag = cols[0].find("a")
            if not link_tag:
                continue

            company = link_tag.get_text(strip=True)
            href = link_tag.get("href", "")
            if href.startswith("/"):
                href = BASE_URL + href

            inspection_date = _parse_date(cols[1].get_text()) if len(cols) > 1 else None

            existing = (
                db.table("fda_483")
                .select("id")
                .eq("source_url", href)
                .execute()
            )
            if existing.data:
                continue

            content = _fetch_observation_content(href)
            db.table("fda_483").insert({
                "company_name": company,
                "inspection_date": inspection_date,
                "source_url": href,
                "content": content,
            }).execute()
            saved += 1
            logger.info(f"저장: {company} ({inspection_date})")
            time.sleep(1.5)

    logger.info(f"FDA 483 수집 완료: {saved}건 신규 저장")
    return saved
```

---

## app/collectors/mfds_notices.py

```python
"""
MFDS(식품의약품안전처) GMP 관련 공지사항 수집기
출처: https://www.mfds.go.kr/brd/m_99/list.do (GMP 공지)
"""

import time
import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from app.database.supabase_client import get_client

logger = logging.getLogger(__name__)

BASE_URL = "https://www.mfds.go.kr"
LIST_URL = "https://www.mfds.go.kr/brd/m_99/list.do"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CKD-QA-Hub/1.0)",
    "Accept-Language": "ko-KR,ko;q=0.9",
}


def _parse_date(text: str) -> str | None:
    text = text.strip()
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _fetch_notice_content(url: str) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "lxml")
        body = soup.find("div", {"class": "board_view"}) or soup.find("td", {"class": "bdcont"})
        return body.get_text(separator="\n", strip=True)[:8000] if body else ""
    except Exception as e:
        logger.warning(f"MFDS 본문 수집 실패 {url}: {e}")
        return ""


def collect(max_pages: int = 2) -> int:
    db = get_client()
    saved = 0

    for page in range(1, max_pages + 1):
        params = {"pageNo": page, "numOfRows": 20}
        try:
            r = requests.get(LIST_URL, headers=HEADERS, params=params, timeout=30)
            r.raise_for_status()
            r.encoding = "utf-8"
        except Exception as e:
            logger.error(f"MFDS 목록 요청 실패 (page={page}): {e}")
            break

        soup = BeautifulSoup(r.text, "lxml")
        rows = soup.select("table tbody tr")
        if not rows:
            break

        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue

            link_tag = row.find("a")
            if not link_tag:
                continue

            title = link_tag.get_text(strip=True)
            href = link_tag.get("href", "")
            if not href.startswith("http"):
                href = BASE_URL + href

            date_text = cols[-1].get_text(strip=True) if cols else None
            published_date = _parse_date(date_text) if date_text else None

            existing = (
                db.table("mfds_notices")
                .select("id")
                .eq("source_url", href)
                .execute()
            )
            if existing.data:
                continue

            content = _fetch_notice_content(href)
            db.table("mfds_notices").insert({
                "title": title,
                "published_date": published_date,
                "source_url": href,
                "content": content,
            }).execute()
            saved += 1
            logger.info(f"MFDS 저장: {title}")
            time.sleep(1.0)

    logger.info(f"MFDS 수집 완료: {saved}건 신규 저장")
    return saved
```

---

## app/ai/gemini_analyzer.py

```python
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
```

---

## app/ai/weekly_briefing.py

```python
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
```

---

## app/utils/charts.py

```python
"""Plotly 차트 유틸리티"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

CKD_BLUE = "#005BAC"
PALETTE = ["#005BAC", "#E8A000", "#D04040", "#2E8B57", "#7B4FBB", "#E85D04", "#0077CC", "#5C4033"]


def risk_heatmap(data: list[dict]) -> go.Figure:
    """GMP 카테고리별 위험도 히트맵"""
    categories = [
        "문서관리", "교육훈련", "일탈관리", "변경관리", "CAPA",
        "데이터완전성", "밸리데이션", "시험실관리", "공급업체관리", "무균보증",
    ]
    sources = ["Warning Letter", "FDA 483", "MFDS 공지"]

    # 데이터에서 카테고리별 빈도 계산
    matrix = {s: {c: 0 for c in categories} for s in sources}
    for item in data:
        ai = item.get("ai_analyses") or {}
        if isinstance(ai, list):
            ai = ai[0] if ai else {}
        gmp_area = ai.get("gmp_area", "") or ""
        src_type = item.get("_source", "Warning Letter")
        for cat in categories:
            if cat.replace(" ", "") in gmp_area.replace(" ", ""):
                matrix[src_type][cat] += 1

    z = [[matrix[s][c] for c in categories] for s in sources]
    fig = go.Figure(go.Heatmap(
        z=z, x=categories, y=sources,
        colorscale=[[0, "#EBF5FB"], [0.5, "#2E86C1"], [1, "#1A5276"]],
        text=[[str(v) if v > 0 else "" for v in row] for row in z],
        texttemplate="%{text}",
        showscale=True,
    ))
    fig.update_layout(
        title="GMP 카테고리별 리스크 히트맵 (최근 3개월)",
        height=280, margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Malgun Gothic, sans-serif"),
    )
    return fig


def monthly_trend(wl_data: list[dict], f483_data: list[dict]) -> go.Figure:
    """월별 이슈 추이 라인 차트"""
    def to_month(items, date_col):
        months: dict[str, int] = {}
        for item in items:
            d = item.get(date_col, "")
            if d and len(d) >= 7:
                m = d[:7]
                months[m] = months.get(m, 0) + 1
        return months

    wl_m = to_month(wl_data, "issued_date")
    f483_m = to_month(f483_data, "inspection_date")
    all_months = sorted(set(list(wl_m.keys()) + list(f483_m.keys())))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=all_months, y=[wl_m.get(m, 0) for m in all_months],
        mode="lines+markers", name="Warning Letter",
        line=dict(color="#D04040", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=all_months, y=[f483_m.get(m, 0) for m in all_months],
        mode="lines+markers", name="FDA 483",
        line=dict(color=CKD_BLUE, width=2),
    ))
    fig.update_layout(
        title="월별 GMP 이슈 추이", height=280,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", y=-0.2),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def country_bar(wl_data: list[dict]) -> go.Figure:
    """국가별 Warning Letter 분포"""
    counts: dict[str, int] = {}
    for item in wl_data:
        c = item.get("country") or "기타"
        counts[c] = counts.get(c, 0) + 1
    df = pd.DataFrame(sorted(counts.items(), key=lambda x: -x[1])[:10], columns=["국가", "건수"])
    fig = px.bar(df, x="건수", y="국가", orientation="h",
                 color_discrete_sequence=[CKD_BLUE])
    fig.update_layout(title="국가별 Warning Letter", height=280,
                      margin=dict(l=10, r=10, t=40, b=10),
                      paper_bgcolor="rgba(0,0,0,0)")
    return fig


def gmp_area_pie(data: list[dict]) -> go.Figure:
    """GMP 영역별 분포 파이 차트"""
    counts: dict[str, int] = {}
    for item in data:
        ai = item.get("ai_analyses") or {}
        if isinstance(ai, list):
            ai = ai[0] if ai else {}
        area = ai.get("gmp_area") or "미분류"
        area = area.split("\n")[0][:20]
        counts[area] = counts.get(area, 0) + 1

    labels = list(counts.keys())[:8]
    values = [counts[l] for l in labels]
    fig = go.Figure(go.Pie(labels=labels, values=values,
                           marker_colors=PALETTE[:len(labels)],
                           hole=0.4))
    fig.update_layout(title="GMP 영역별 분포", height=280,
                      margin=dict(l=10, r=10, t=40, b=10),
                      paper_bgcolor="rgba(0,0,0,0)")
    return fig
```

---

## app/utils/export.py

```python
"""Excel / PDF 내보내기"""

import io
import pandas as pd


def to_excel(data: list[dict], sheet_name: str = "데이터") -> bytes:
    """데이터를 Excel 바이트로 변환"""
    rows = []
    for item in data:
        ai = item.get("ai_analyses") or {}
        if isinstance(ai, list):
            ai = ai[0] if ai else {}
        row = {
            "업체명": item.get("company_name") or item.get("title", ""),
            "국가": item.get("country", ""),
            "날짜": item.get("issued_date") or item.get("inspection_date") or item.get("published_date", ""),
            "AI 요약": ai.get("summary", ""),
            "GMP 영역": ai.get("gmp_area", ""),
            "위험도": ai.get("risk_level", ""),
            "종근당 영향도": ai.get("ckd_impact", ""),
            "권장 조치": ai.get("recommended_action", ""),
            "원문 링크": item.get("source_url", ""),
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        ws = writer.sheets[sheet_name]
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 60)
    return buf.getvalue()
```

---

## Home.py (Streamlit 진입점)

```python
import streamlit as st

st.set_page_config(
    page_title="종근당 QA Intelligence Hub",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #003B75; }
    [data-testid="stSidebar"] * { color: white !important; }
    .stMetric { background: #F0F4F8; border-radius: 10px; padding: 12px; }
    .risk-high { color: #C0392B; font-weight: bold; }
    .risk-medium { color: #E67E22; font-weight: bold; }
    .risk-low { color: #27AE60; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("💊 종근당 QA Intelligence Hub")
st.markdown("**AI 기반 품질 인텔리전스 플랫폼** | 왼쪽 메뉴에서 기능을 선택하세요.")

col1, col2, col3 = st.columns(3)
with col1:
    st.info("📋 **GMP 규제 동향**\nFDA · EMA · MFDS 최신 규제")
with col2:
    st.warning("⚠️ **Warning Letter / FDA 483**\nAI 심층 분석 및 종근당 영향도")
with col3:
    st.error("🔍 **데이터 완전성 모니터링**\nALCOA+ 기반 자동 분류")
```

---

## app/pages/1_대시보드.py

```python
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from app.database.supabase_client import (
    fetch_warning_letters, fetch_fda_483, fetch_mfds_notices,
    fetch_weekly_briefing, count_new_this_week,
)
from app.utils.charts import risk_heatmap, monthly_trend, country_bar

st.set_page_config(page_title="대시보드 | 종근당 QA Hub", layout="wide")
st.title("📊 대시보드")

# ── KPI 카드 ──────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    n = count_new_this_week("warning_letters", "issued_date")
    st.metric("신규 Warning Letter", n, delta="이번 주")
with c2:
    n = count_new_this_week("fda_483", "inspection_date")
    st.metric("신규 FDA 483", n, delta="이번 주")
with c3:
    n = count_new_this_week("mfds_notices", "published_date")
    st.metric("신규 MFDS 공지", n, delta="이번 주")
with c4:
    wl_data = fetch_warning_letters(limit=50)
    high_risk = sum(
        1 for w in wl_data
        if (w.get("ai_analyses") or [{}])[0].get("risk_level", "").lower() == "high"
    )
    st.metric("고위험 항목", high_risk, delta="전체 누적")

st.divider()

# ── 주간 브리핑 ───────────────────────────────────────────
today = date.today()
week_start = (today - timedelta(days=today.weekday())).isoformat()
briefing = fetch_weekly_briefing(week_start)

col_brief, col_chart = st.columns([1.2, 1])

with col_brief:
    st.subheader("📋 이번 주 QA 브리핑")
    if briefing and briefing.get("briefing_content"):
        st.markdown(briefing["briefing_content"])
    else:
        st.info("이번 주 브리핑이 아직 생성되지 않았습니다. 월요일 오전 6시 자동 생성됩니다.")
        if st.button("지금 생성하기"):
            with st.spinner("Gemini AI가 브리핑을 생성 중입니다..."):
                from app.ai.weekly_briefing import generate
                content = generate()
                st.success("브리핑 생성 완료!")
                st.markdown(content)

with col_chart:
    st.subheader("🌡️ 글로벌 GMP 리스크 히트맵")
    all_data = [{"_source": "Warning Letter", **w} for w in wl_data]
    all_data += [{"_source": "FDA 483", **f} for f in fetch_fda_483(limit=50)]
    fig = risk_heatmap(all_data)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── 차트 행 ───────────────────────────────────────────────
c1, c2 = st.columns(2)
with c1:
    f483_data = fetch_fda_483(limit=100)
    fig = monthly_trend(wl_data, f483_data)
    st.plotly_chart(fig, use_container_width=True)
with c2:
    fig = country_bar(wl_data)
    st.plotly_chart(fig, use_container_width=True)
```

---

## app/pages/3_Warning_Letter.py

```python
import streamlit as st
import pandas as pd
from app.database.supabase_client import fetch_warning_letters
from app.utils.charts import gmp_area_pie, country_bar
from app.utils.export import to_excel

st.set_page_config(page_title="Warning Letter | 종근당 QA Hub", layout="wide")
st.title("⚠️ Warning Letter 분석")

# ── 데이터 로드 ───────────────────────────────────────────
@st.cache_data(ttl=300)
def load():
    return fetch_warning_letters(limit=200)

data = load()

# ── 필터 ─────────────────────────────────────────────────
with st.expander("🔍 검색 및 필터", expanded=True):
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        query = st.text_input("업체명 / 국가 검색")
    with fc2:
        risk_filter = st.selectbox("위험도", ["전체", "High", "Medium", "Low"])
    with fc3:
        sort_by = st.selectbox("정렬", ["최신순", "위험도순"])

# 필터링
filtered = data
if query:
    filtered = [d for d in filtered if query.lower() in (d.get("company_name", "") + d.get("country", "")).lower()]
if risk_filter != "전체":
    filtered = [
        d for d in filtered
        if ((d.get("ai_analyses") or [{}])[0] if isinstance(d.get("ai_analyses"), list) else (d.get("ai_analyses") or {})).get("risk_level", "").lower() == risk_filter.lower()
    ]
if sort_by == "위험도순":
    order = {"high": 0, "medium": 1, "low": 2}
    filtered.sort(key=lambda x: order.get(((x.get("ai_analyses") or [{}])[0] if isinstance(x.get("ai_analyses"), list) else (x.get("ai_analyses") or {})).get("risk_level", "low").lower(), 3))

# ── 내보내기 ─────────────────────────────────────────────
col_info, col_export = st.columns([3, 1])
with col_info:
    st.caption(f"총 {len(filtered)}건")
with col_export:
    if st.button("📥 Excel 내보내기"):
        excel_bytes = to_excel(filtered, "Warning_Letters")
        st.download_button("⬇️ 다운로드", excel_bytes, "warning_letters.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ── 목록 ─────────────────────────────────────────────────
RISK_COLOR = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}

for item in filtered:
    ai = item.get("ai_analyses") or {}
    if isinstance(ai, list):
        ai = ai[0] if ai else {}

    risk = ai.get("risk_level", "N/A")
    icon = RISK_COLOR.get(risk, "⚪")
    header = f"{icon} **{item.get('company_name', 'N/A')}** | {item.get('country', '')} | {item.get('issued_date', '')}"

    with st.expander(header):
        t1, t2 = st.tabs(["AI 분석", "원문 정보"])
        with t1:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**📝 AI 요약**\n\n{ai.get('summary', '분석 데이터 없음')}")
                st.markdown(f"**🔍 Root Cause**\n\n{ai.get('root_cause', '-')}")
                st.markdown(f"**📋 GMP 위반 영역**\n\n{ai.get('gmp_area', '-')}")
                st.markdown(f"**🔧 예상 CAPA**\n\n{ai.get('capa', '-')}")
            with col2:
                st.markdown(f"**💡 Lessons Learned**\n\n{ai.get('lessons_learned', '-')}")
                st.markdown(f"**🏭 종근당 영향도**\n\n{ai.get('ckd_impact', '-')}")
                st.markdown(f"**✅ 권장 조치사항**\n\n{ai.get('recommended_action', '-')}")
        with t2:
            st.markdown(f"**원문 링크:** [{item.get('source_url', '')}]({item.get('source_url', '')})")
            if item.get("content"):
                st.text_area("원문 내용 (일부)", item["content"][:1000], height=200, disabled=True)

st.divider()

# ── 차트 ─────────────────────────────────────────────────
st.subheader("📊 분포 분석")
cc1, cc2 = st.columns(2)
with cc1:
    st.plotly_chart(gmp_area_pie(filtered), use_container_width=True)
with cc2:
    st.plotly_chart(country_bar(filtered), use_container_width=True)
```

---

## app/pages/4_FDA_483.py

```python
import streamlit as st
from app.database.supabase_client import fetch_fda_483
from app.utils.charts import gmp_area_pie
from app.utils.export import to_excel

st.set_page_config(page_title="FDA 483 | 종근당 QA Hub", layout="wide")
st.title("🔍 FDA 483 분석")

@st.cache_data(ttl=300)
def load():
    return fetch_fda_483(limit=200)

data = load()

with st.expander("🔍 검색 및 필터", expanded=True):
    fc1, fc2 = st.columns(2)
    with fc1:
        query = st.text_input("업체명 검색")
    with fc2:
        risk_filter = st.selectbox("위험도", ["전체", "High", "Medium", "Low"])

filtered = data
if query:
    filtered = [d for d in filtered if query.lower() in d.get("company_name", "").lower()]
if risk_filter != "전체":
    filtered = [
        d for d in filtered
        if ((d.get("ai_analyses") or [{}])[0] if isinstance(d.get("ai_analyses"), list) else (d.get("ai_analyses") or {})).get("risk_level", "").lower() == risk_filter.lower()
    ]

col_info, col_export = st.columns([3, 1])
with col_info:
    st.caption(f"총 {len(filtered)}건")
with col_export:
    if st.button("📥 Excel 내보내기"):
        excel_bytes = to_excel(filtered, "FDA_483")
        st.download_button("⬇️ 다운로드", excel_bytes, "fda_483.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

RISK_COLOR = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}
for item in filtered:
    ai = item.get("ai_analyses") or {}
    if isinstance(ai, list):
        ai = ai[0] if ai else {}

    risk = ai.get("risk_level", "N/A")
    repeated = "🔁 반복 지적" if "반복" in (ai.get("root_cause") or "") else ""
    header = f"{RISK_COLOR.get(risk,'⚪')} **{item.get('company_name','N/A')}** | {item.get('inspection_date','')} {repeated}"

    with st.expander(header):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**📝 주요 Observation 요약**\n\n{ai.get('summary', '-')}")
            st.markdown(f"**📋 GMP 카테고리**\n\n{ai.get('gmp_area', '-')}")
            st.markdown(f"**🔄 반복 지적 여부**\n\n{ai.get('root_cause', '-')}")
        with col2:
            st.markdown(f"**⚠️ 품질 리스크**\n\n{ai.get('lessons_learned', '-')}")
            st.markdown(f"**🏭 종근당 영향도**\n\n{ai.get('ckd_impact', '-')}")
            st.markdown(f"**✅ 권장 조치사항**\n\n{ai.get('recommended_action', '-')}")
        st.markdown(f"[원문 보기]({item.get('source_url','')})")

st.divider()
st.plotly_chart(gmp_area_pie(filtered), use_container_width=True)
```

---

## app/pages/5_데이터완전성.py

```python
"""
ALCOA+ 기반 데이터 완전성(Data Integrity) 모니터링
"""

import streamlit as st
from app.database.supabase_client import get_client

st.set_page_config(page_title="데이터 완전성 | 종근당 QA Hub", layout="wide")
st.title("🔒 데이터 완전성 모니터링")
st.caption("ALCOA+ 원칙 기반 — Warning Letter 및 FDA 483 AI 자동 분류")

ALCOA_ITEMS = [
    ("Attributable", "귀속성", "데이터 작성자·시스템이 명확히 식별되는가"),
    ("Legible", "판독성", "데이터가 영구적으로 판독 가능한가"),
    ("Contemporaneous", "동시성", "활동 발생 시점에 즉시 기록되었는가"),
    ("Original", "원본성", "원본 또는 진본 사본이 보존되는가"),
    ("Accurate", "정확성", "오류 없이 정확하게 기록되었는가"),
    ("Complete", "완전성", "모든 데이터가 누락 없이 기록되었는가"),
    ("Consistent", "일관성", "날짜·버전·단위가 일관되게 사용되는가"),
    ("Enduring", "내구성", "저장 매체가 기록 보존 기간을 지원하는가"),
    ("Available", "가용성", "검토·감사 시 데이터에 접근 가능한가"),
]

# 탭: ALCOA+ 항목 설명 | 사례 분석
tab1, tab2 = st.tabs(["📖 ALCOA+ 항목 현황", "🔍 위반 사례 분석"])

with tab1:
    db = get_client()
    analyses = db.table("ai_analyses").select("alcoa_category,source_type,risk_level").not_.is_("alcoa_category", "null").execute().data

    # 항목별 집계
    counts: dict[str, int] = {a[0]: 0 for a in ALCOA_ITEMS}
    for row in analyses:
        cat = row.get("alcoa_category", "") or ""
        for a_name, _, _ in ALCOA_ITEMS:
            if a_name.lower() in cat.lower():
                counts[a_name] += 1

    cols = st.columns(3)
    for i, (name, kor, desc) in enumerate(ALCOA_ITEMS):
        with cols[i % 3]:
            cnt = counts.get(name, 0)
            color = "#D04040" if cnt >= 3 else "#E67E22" if cnt >= 1 else "#27AE60"
            st.markdown(f"""
<div style="border:1px solid {color};border-radius:8px;padding:12px;margin-bottom:10px;">
<b style="color:{color}">{name}</b> ({kor})<br>
<small style="color:#666">{desc}</small><br>
<b style="font-size:22px;color:{color}">{cnt}건</b> 위반 사례
</div>
""", unsafe_allow_html=True)

with tab2:
    di_cases = (
        db.table("ai_analyses")
        .select("source_type,source_id,summary,root_cause,ckd_impact,recommended_action,alcoa_category,risk_level")
        .not_.is_("alcoa_category", "null")
        .neq("alcoa_category", "해당없음")
        .order("risk_level")
        .execute()
        .data
    )

    if not di_cases:
        st.info("데이터 완전성 위반 사례가 아직 분류되지 않았습니다.")
    else:
        for case in di_cases:
            risk = case.get("risk_level", "")
            icon = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(risk, "⚪")
            header = f"{icon} [{case.get('source_type','').upper()}] ALCOA: {case.get('alcoa_category','')}"
            with st.expander(header):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**사례 요약**\n\n{case.get('summary','-')}")
                    st.markdown(f"**Root Cause**\n\n{case.get('root_cause','-')}")
                with c2:
                    st.markdown(f"**종근당 영향도**\n\n{case.get('ckd_impact','-')}")
                    st.markdown(f"**권장 조치사항**\n\n{case.get('recommended_action','-')}")
```

---

## scripts/run_weekly.py

```python
"""
주간 자동 실행 스크립트
GitHub Actions에서 호출됨
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run_weekly")


def main():
    logger.info("=== 종근당 QA Intelligence Hub 주간 수집 시작 ===")

    # 1. 데이터 수집
    from app.collectors.fda_warning_letters import collect as collect_wl
    from app.collectors.fda_483 import collect as collect_483
    from app.collectors.mfds_notices import collect as collect_mfds

    wl_count = collect_wl(max_pages=3)
    f483_count = collect_483(max_pages=3)
    mfds_count = collect_mfds(max_pages=2)
    logger.info(f"수집 완료 — WL:{wl_count}, 483:{f483_count}, MFDS:{mfds_count}")

    # 2. AI 분석
    from app.ai.gemini_analyzer import run_all_analyses
    analyzed = run_all_analyses()
    logger.info(f"AI 분석 완료: {analyzed}건")

    # 3. 주간 브리핑 생성
    from app.ai.weekly_briefing import generate
    briefing = generate()
    logger.info("주간 브리핑 생성 완료")
    logger.info("=== 주간 작업 완료 ===")


if __name__ == "__main__":
    main()
```

---

## .github/workflows/weekly_collect.yml

```yaml
name: 주간 QA 데이터 수집 및 AI 분석

on:
  schedule:
    - cron: "0 21 * * 0"   # 매주 일요일 21:00 UTC = 월요일 06:00 KST
  workflow_dispatch:         # 수동 실행 가능

jobs:
  collect-and-analyze:
    runs-on: ubuntu-latest
    timeout-minutes: 60

    steps:
      - name: 소스 체크아웃
        uses: actions/checkout@v4

      - name: Python 3.11 설정
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: 의존성 설치
        run: pip install -r requirements.txt

      - name: 환경 변수 설정
        run: |
          echo "SUPABASE_URL=${{ secrets.SUPABASE_URL }}" >> $GITHUB_ENV
          echo "SUPABASE_KEY=${{ secrets.SUPABASE_KEY }}" >> $GITHUB_ENV
          echo "GEMINI_API_KEY=${{ secrets.GEMINI_API_KEY }}" >> $GITHUB_ENV

      - name: 주간 수집 및 분석 실행
        run: python scripts/run_weekly.py

      - name: 결과 알림 (Slack, 선택사항)
        if: always()
        run: |
          echo "수집 완료: $(date '+%Y-%m-%d %H:%M:%S KST')"
```

---

## README.md (설치 가이드)

```markdown
# 종근당 QA Intelligence Hub

## 사전 준비

1. **Supabase 프로젝트 생성** → URL과 anon key 복사
2. **Supabase SQL Editor**에서 `app/database/schema.sql` 실행
3. **Google Gemini API 키** 발급 (https://aistudio.google.com)

## 로컬 실행

\```bash
git clone https://github.com/your-org/ckd-qa-hub
cd ckd-qa-hub
pip install -r requirements.txt
cp .env.example .env   # .env 파일에 키 입력
streamlit run Home.py
\```

## Streamlit Community Cloud 배포

1. GitHub에 저장소 Push
2. https://share.streamlit.io → New app → 저장소 선택
3. Secrets 탭에서 환경변수 입력:
   \```
   SUPABASE_URL = "..."
   SUPABASE_KEY = "..."
   GEMINI_API_KEY = "..."
   \```

## GitHub Actions Secrets 설정

Settings → Secrets and variables → Actions에서 아래 3개 등록:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `GEMINI_API_KEY`

## 수동 데이터 수집

\```bash
python scripts/run_weekly.py
\```
```
