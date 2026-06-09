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


def _parse_date(text: str) -> str:
    """날짜 파싱"""
    text = text.strip()
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return datetime.now().date().isoformat()


def _fetch_notice_content(url: str) -> str:
    """공지사항 본문 수집"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        r.raise_for_status()
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        
        # 본문 영역 찾기 (MFDS 페이지 구조에 맞게)
        body = (
            soup.find("div", {"class": "board_view"}) or 
            soup.find("td", {"class": "bdcont"}) or 
            soup.find("div", class_=lambda x: x and "view" in x.lower())
        )
        
        if not body:
            return ""
        
        return body.get_text(separator="\n", strip=True)[:8000]
    except Exception as e:
        logger.warning(f"MFDS 본문 수집 실패 {url}: {e}")
        return ""


def collect(max_pages: int = 3) -> int:
    """MFDS GMP 관련 공지사항 수집"""
    db = get_client()
    saved = 0

    for page in range(1, max_pages + 1):
        params = {
            "pageNo": page,
            "numOfRows": 20,
            "srchWord": ""  # 필요시 검색어 추가 가능
        }
        
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
            logger.info("더 이상 데이터가 없습니다.")
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
            if not href:
                continue
            if not href.startswith("http"):
                href = BASE_URL + href

            # 날짜는 보통 마지막 컬럼
            date_text = cols[-1].get_text(strip=True) if len(cols) > 0 else ""
            published_date = _parse_date(date_text)

            # 중복 체크
            existing = db.table("mfds_notices").select("id").eq("source_url", href).execute()
            if existing.data:
                continue

            content = _fetch_notice_content(href)

            try:
                db.table("mfds_notices").insert({
                    "title": title,
                    "published_date": published_date,
                    "source_url": href,
                    "content": content or "",
                }).execute()

                saved += 1
                logger.info(f"✅ MFDS 저장: {title[:80]}...")
                time.sleep(1.1)
            except Exception as e:
                logger.error(f"❌ MFDS DB 저장 실패: {title[:60]}... {e}")

    logger.info(f"MFDS 수집 완료 — 신규 {saved}건 저장")
    return saved
