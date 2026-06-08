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
        soup = BeautifulSoup(r.text, "html.parser")
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
