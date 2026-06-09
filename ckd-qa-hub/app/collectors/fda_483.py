import time
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from app.database.supabase_client import get_client

logger = logging.getLogger(__name__)

BASE_URL = "https://www.fda.gov"
LIST_URL = "https://www.fda.gov/about-fda/office-inspections-and-investigations/oii-foia-electronic-reading-room"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CKD-QA-Hub/1.0)"
}


def _fetch_pdf_content(pdf_url: str) -> str:
    """PDF에서 텍스트 추출 시도 (현재는 링크만 저장, 필요시 pdfplumber 추가 가능)"""
    return f"PDF 다운로드 링크: {pdf_url}"   # 추후 PDF 파싱 기능 추가 가능


def collect(max_pages: int = 1) -> int:   # 이 페이지는 페이지네이션이 별도로 있을 수 있음
    db = get_client()
    saved = 0

    try:
        r = requests.get(LIST_URL, headers=HEADERS, timeout=40)
        r.raise_for_status()
    except Exception as e:
        logger.error(f"목록 페이지 로드 실패: {e}")
        return 0

    soup = BeautifulSoup(r.text, "html.parser")
    rows = soup.select("table tbody tr")

    logger.info(f"483 테이블 행 발견: {len(rows)}개")

    for row in rows:
        try:
            cols = row.find_all("td")
            if len(cols) < 4:
                continue

            # 날짜
            record_date = cols[0].get_text(strip=True)
            
            # 회사명
            company = cols[1].get_text(strip=True)
            
            # 483 링크
            link_tag = cols[3].find("a")
            if not link_tag:
                continue
                
            pdf_href = link_tag.get("href")
            if pdf_href.startswith("/"):
                pdf_url = BASE_URL + pdf_href
            else:
                pdf_url = pdf_href

            # 중복 체크
            existing = db.table("fda_483").select("id").eq("source_url", pdf_url).execute()
            if existing.data:
                continue

            content = _fetch_pdf_content(pdf_url)

            db.table("fda_483").insert({
                "company_name": company,
                "inspection_date": record_date,   # 실제 검사일은 PDF 안에 있음
                "source_url": pdf_url,
                "content": content,
            }).execute()

            saved += 1
            logger.info(f"✅ 저장 완료: {company}")
            time.sleep(1.0)

        except Exception as e:
            logger.warning(f"행 처리 중 오류: {e}")
            continue

    logger.info(f"FDA 483 수집 완료 — {saved}건 신규 저장")
    return saved
