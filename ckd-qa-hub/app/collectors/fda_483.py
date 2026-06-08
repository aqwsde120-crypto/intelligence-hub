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
