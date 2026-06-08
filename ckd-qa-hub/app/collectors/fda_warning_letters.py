import time
import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup

from app.database.supabase_client import get_client

logger = logging.getLogger(**name**)

BASE_URL = "https://www.fda.gov"

LIST_URL = (
"https://www.fda.gov/inspections-compliance-enforcement-and-criminal-"
"investigations/compliance-actions-and-activities/warning-letters"
)

HEADERS = {
"User-Agent": "Mozilla/5.0 (compatible; CKD-QA-Hub/1.0)"
}

def _parse_date(text: str):
text = text.strip()

```
for fmt in (
    "%B %d, %Y",
    "%m/%d/%Y",
    "%Y-%m-%d",
):
    try:
        return datetime.strptime(text, fmt).date().isoformat()
    except Exception:
        pass

return None
```

def _fetch_letter_content(url: str) -> str:
try:
r = requests.get(
url,
headers=HEADERS,
timeout=30,
)
r.raise_for_status()

```
    soup = BeautifulSoup(
        r.text,
        "html.parser"
    )

    main = (
        soup.find("main")
        or soup.find("div", class_="lcds-text-field")
    )

    if not main:
        return ""

    return main.get_text(
        separator="\n",
        strip=True
    )[:10000]

except Exception as e:
    logger.warning(
        f"본문 수집 실패: {url} / {e}"
    )
    return ""
```

def collect(max_pages: int = 5) -> int:

```
db = get_client()
saved = 0

for page in range(max_pages):

    if page == 0:
        url = LIST_URL
    else:
        url = f"{LIST_URL}?page={page}"

    logger.info(f"수집 페이지: {url}")

    try:
        r = requests.get(
            url,
            headers=HEADERS,
            timeout=30,
        )
        r.raise_for_status()

    except Exception as e:
        logger.error(
            f"페이지 요청 실패: {e}"
        )
        break

    soup = BeautifulSoup(
        r.text,
        "html.parser"
    )

    rows = soup.select(
        "table tbody tr"
    )

    logger.info(
        f"발견 건수: {len(rows)}"
    )

    if not rows:
        break

    for row in rows:

        cols = row.find_all("td")

        if len(cols) < 2:
            continue

        link = cols[0].find("a")

        if not link:
            continue

        company_name = link.get_text(
            strip=True
        )

        href = link.get("href")

        if not href:
            continue

        if href.startswith("/"):
            href = BASE_URL + href

        issued_date = None

        if len(cols) >= 2:
            issued_date = _parse_date(
                cols[1].get_text()
            )

        country = None

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

        try:

            db.table(
                "warning_letters"
            ).insert(
                {
                    "company_name": company_name,
                    "country": country,
                    "issued_date": issued_date,
                    "source_url": href,
                    "content": content,
                }
            ).execute()

            saved += 1

            logger.info(
                f"저장 완료: {company_name}"
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
```
if st.button("FDA Warning Letter 수집"):
    from app.collectors.fda_warning_letters import collect

    with st.spinner("수집 중..."):
        count = collect()

    st.success(f"{count}건 저장 완료")
