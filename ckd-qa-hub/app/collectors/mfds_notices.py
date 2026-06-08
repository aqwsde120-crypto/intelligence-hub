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
        soup = BeautifulSoup(r.text, "html.parser")
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

        soup = BeautifulSoup(r.text, "html.parser")
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
