"""
FDA Warning Letter 수집기 (RSS 기반)
"""

import logging
import time
from datetime import datetime

import feedparser
import requests
from bs4 import BeautifulSoup

from app.database.supabase_client import get_client

logger = logging.getLogger(__name__)

RSS_URL = "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/warning-letters/rss.xml"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CKD-QA-Hub/1.0)"
}


def _fetch_letter_content(url: str) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")

        main = (
            soup.find("main")
            or soup.find("article")
            or soup.find("div", {"class": "field__item"})
        )

        if not main:
            return ""

        return main.get_text(separator="\n", strip=True)[:10000]

    except Exception as e:
        logger.warning(f"본문 수집 실패: {url} / {e}")
        return ""


def _parse_date(entry):
    try:
        return datetime(*entry.published_parsed[:6]).date().isoformat()
    except Exception:
        return None


def collect(max_items: int = 50) -> int:
    db = get_client()

    feed = feedparser.parse(RSS_URL)

    if not feed.entries:
        logger.warning("FDA RSS 데이터 없음")
        return 0

    saved = 0

    for entry in feed.entries[:max_items]:

        source_url = entry.link

        existing = (
            db.table("warning_letters")
            .select("id")
            .eq("source_url", source_url)
            .execute()
        )

        if existing.data:
            continue

        title = entry.title

        issued_date = _parse_date(entry)

        content = _fetch_letter_content(source_url)

        record = {
            "company_name": title,
            "country": None,
            "issued_date": issued_date,
            "source_url": source_url,
            "content": content,
        }

        try:
            db.table("warning_letters").insert(record).execute()

            saved += 1

            logger.info(
                f"저장 완료: {title} ({issued_date})"
            )

            time.sleep(1)

        except Exception as e:
            logger.error(f"DB 저장 실패: {e}")

    logger.info(f"Warning Letter 신규 저장: {saved}건")

    return saved
