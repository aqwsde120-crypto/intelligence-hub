import time
import logging
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
    "User-Agent": "Mozilla/5.0"
}


def _fetch_letter_content(url):

    try:
        r = requests.get(
            url,
            headers=HEADERS,
            timeout=30,
        )

        r.raise_for_status()

        soup = BeautifulSoup(
            r.text,
            "html.parser"
        )

        main = soup.find("main")

        if not main:
            return ""

        return main.get_text(
            separator="\n",
            strip=True
        )[:10000]

    except Exception as e:

        logger.warning(
            f"본문 수집 실패: {e}"
        )

        return ""


def collect(max_items=50):

    db = get_client()

    saved = 0

    try:

        r = requests.get(
            LIST_URL,
            headers=HEADERS,
            timeout=30,
        )

        r.raise_for_status()

    except Exception as e:

        logger.error(
            f"목록 수집 실패: {e}"
        )

        return 0

    soup = BeautifulSoup(
        r.text,
        "html.parser"
    )

    links = soup.find_all("a")

    warning_links = []

    for a in links:

        href = a.get("href")

        if not href:
            continue

        if "/warning-letters/" not in href:
            continue

        if href.startswith("/"):
            href = BASE_URL + href

        title = a.get_text(strip=True)

        if not title:
            continue

        warning_links.append(
            (title, href)
        )

    logger.info(
        f"Warning Letter 발견: {len(warning_links)}건"
    )

    for title, href in warning_links[:max_items]:

        try:

            existing = (
                db.table("warning_letters")
                .select("id")
                .eq("source_url", href)
                .execute()
            )

            if existing.data:
                continue

            content = _fetch_letter_content(
                href
            )

            db.table(
                "warning_letters"
            ).insert(
                {
                    "company_name": title,
                    "country": None,
                    "issued_date": datetime.now().date().isoformat(),
                    "source_url": href,
                    "content": content,
                }
            ).execute()

            saved += 1

            logger.info(
                f"저장 완료: {title}"
            )

            time.sleep(1)

        except Exception as e:

            logger.error(
                f"DB 저장 실패: {e}"
            )

    logger.info(
        f"Warning Letter 신규 저장: {saved}건"
    )

    return saved
