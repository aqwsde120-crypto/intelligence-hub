import time
import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from app.database.supabase_client import get_client

logger = logging.getLogger(__name__)

BASE_URL = "https://www.fda.gov"
LIST_URL = "https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/inspection-references/inspection-observations"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CKD-QA-Hub/1.0)",
    "Accept-Language": "en-US,en;q=0.9"
}


def _fetch_observation_content(url: str) -> str:
    """FDA 483 본문 내용 수집"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        
        main = (
            soup.find("main") or 
            soup.find("article") or 
            soup.find("div", {"id": "main-content"}) or
            soup.find("div", class_=lambda x: x and "node__content" in x)
        )
        
        if not main:
            return ""
        
        return main.get_text(separator="\n", strip=True)[:8000]
    except Exception as e:
        logger.warning(f"본문 수집 실패 {url}: {e}")
        return ""


def collect(max_pages: int = 4) -> int:
    """FDA 483 데이터 수집"""
    db = get_client()
    saved = 0

    for page in range(max_pages):
        url = f"{LIST_URL}?page={page}" if page > 0 else LIST_URL
        
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
        except Exception as e:
            logger.error(f"FDA 483 목록 요청 실패 (page={page}): {e}")
            break

        soup = BeautifulSoup(r.text, "html.parser")
        
        # 테이블 행 찾기 (FDA 페이지 구조에 맞게 여러 패턴 시도)
        rows = soup.select("table tbody tr") or soup.select("div.view-content div.views-row")
        
        if not rows:
            logger.info(f"page {page}에 데이터가 없습니다.")
            continue

        for row in rows:
            try:
                # 링크와 회사명 찾기
                link_tag = row.find("a")
                if not link_tag:
                    continue
                
                company = link_tag.get_text(strip=True)
                href = link_tag.get("href", "")
                if not href:
                    continue
                if href.startswith("/"):
                    href = BASE_URL + href

                # 날짜 찾기 (여러 위치 시도)
                date_text = ""
                date_tags = row.find_all("td") or row.find_all("span", class_=lambda x: x and "date" in x.lower())
                if date_tags:
                    date_text = date_tags[-1].get_text(strip=True)

                # 날짜 파싱
                inspection_date = None
                try:
                    if "/" in date_text:
                        inspection_date = datetime.strptime(date_text.strip(), "%m/%d/%Y").date().isoformat()
                except:
                    inspection_date = datetime.now().date().isoformat()

                # 중복 체크
                existing = db.table("fda_483").select("id").eq("source_url", href).execute()
                if existing.data:
                    continue

                content = _fetch_observation_content(href)

                db.table("fda_483").insert({
                    "company_name": company.strip(),
                    "inspection_date": inspection_date,
                    "source_url": href,
                    "content": content or "",
                }).execute()

                saved += 1
                logger.info(f"✅ FDA 483 저장: {company[:70]}...")
                time.sleep(1.3)

            except Exception as e:
                logger.error(f"행 처리 실패: {e}")
                continue

    logger.info(f"FDA 483 수집 완료 — 총 {saved}건 신규 저장")
    return saved
