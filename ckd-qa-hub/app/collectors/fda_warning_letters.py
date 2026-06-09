import time
import logging
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from app.database.supabase_client import get_client

logger = logging.getLogger(__name__)

BASE_URL = "https://www.fda.gov"
LIST_URL = (
    "https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/"
    "compliance-actions-and-activities/warning-letters"
)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CKD-QA-Hub/1.0)"
}


def _fetch_letter_content(url: str) -> str:
    """Warning Letter 본문 수집"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        main = soup.find("main") or soup.find("article")
        if not main:
            return ""
        return main.get_text(separator="\n", strip=True)[:10000]
    except Exception as e:
        logger.warning(f"본문 수집 실패 {url}: {e}")
        return ""


def _parse_issued_date(text: str) -> str:
    """날짜 파싱"""
    date_patterns = [
        r'(\d{1,2}/\d{1,2}/\d{4})',
        r'(\d{4}-\d{1,2}-\d{1,2})',
        r'([A-Za-z]+ \d{1,2}, \d{4})'
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            date_str = match.group(1)
            for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%B %d, %Y"):
                try:
                    return datetime.strptime(date_str, fmt).date().isoformat()
                except:
                    continue
    return datetime.now().date().isoformat()


def collect(max_items: int = 30) -> int:
    """Warning Letter 데이터 수집"""
    db = get_client()
    saved = 0

    try:
        r = requests.get(LIST_URL, headers=HEADERS, timeout=30)
        r.raise_for_status()
    except Exception as e:
        logger.error(f"목록 페이지 요청 실패: {e}")
        return 0

    soup = BeautifulSoup(r.text, "html.parser")
    
    # Warning Letter 링크 추출
    warning_links = []
    for a in soup.find_all("a", href=True):
        href = a.get("href")
        if href and "/warning-letters/" in href:
            if href.startswith("/"):
                href = BASE_URL + href
            title = a.get_text(strip=True)
            if title and len(title) > 10:
                warning_links.append((title, href))

    logger.info(f"Warning Letter 링크 발견: {len(warning_links)}건")

    for title, href in warning_links[:max_items]:
        try:
            # 중복 체크
            existing = db.table("warning_letters").select("id").eq("source_url", href).execute()
            if existing.data:
                continue

            content = _fetch_letter_content(href)
            issued_date = _parse_issued_date(title + " " + content[:500])

            db.table("warning_letters").insert({
                "company_name": title.strip(),
                "country": None,
                "issued_date": issued_date,
                "source_url": href,
                "content": content or "",
            }).execute()

            saved += 1
            logger.info(f"✅ 저장 완료: {title[:80]}...")
            time.sleep(1.2)

        except Exception as e:
            logger.error(f"❌ 저장 실패 ({title[:60]}...): {e}")

    logger.info(f"Warning Letter 수집 완료 — 신규 {saved}건")
    return saved
