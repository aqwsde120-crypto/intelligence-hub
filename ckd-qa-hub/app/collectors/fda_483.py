import time
import logging
import requests
import pandas as pd
from datetime import datetime
from app.database.supabase_client import get_client

logger = logging.getLogger(__name__)

BASE_URL = "https://www.fda.gov"
EXCEL_URLS = {
    "FY2025": "https://www.fda.gov/media/190190/download",
    "FY2024": "https://www.fda.gov/media/185090/download",
    "FY2023": "https://www.fda.gov/media/174101/download",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CKD-QA-Hub/1.0)"
}


def collect(max_pages: int = 3) -> int:   # max_pages는 이제 무시됨 (Excel 기반)
    """FDA 483 Excel 파일 다운로드 → DB 저장"""
    db = get_client()
    saved = 0

    for fy_name, url in EXCEL_URLS.items():
        logger.info(f"{fy_name} Excel 다운로드 중...")
        try:
            r = requests.get(url, headers=HEADERS, timeout=60)
            r.raise_for_status()
            
            # Excel 읽기
            df = pd.read_excel(r.content)
            
            logger.info(f"{fy_name} 데이터 로드 완료: {len(df)} rows")
            
            for _, row in df.iterrows():
                try:
                    company = str(row.get("Firm Name", row.get("Company", ""))).strip()
                    if not company or company.lower() == "nan":
                        continue

                    # 날짜 처리
                    date_col = None
                    for col in ["Inspection Date", "Date", "inspection_date"]:
                        if col in row:
                            date_col = col
                            break
                    
                    inspection_date = datetime.now().date().isoformat()
                    if date_col and pd.notna(row[date_col]):
                        try:
                            inspection_date = pd.to_datetime(row[date_col]).date().isoformat()
                        except:
                            pass

                    source_url = ""  # Excel에는 개별 링크가 없을 수 있음

                    # 중복 체크 (회사명 + 날짜 기준)
                    existing = db.table("fda_483")\
                        .select("id")\
                        .eq("company_name", company)\
                        .eq("inspection_date", inspection_date)\
                        .execute()

                    if existing.data:
                        continue

                    # content는 Excel에 없으므로 요약 정보로 대체
                    content = f"FY: {fy_name}\n" + "\n".join([f"{col}: {row[col]}" for col in df.columns[:10] if pd.notna(row[col])])

                    db.table("fda_483").insert({
                        "company_name": company,
                        "inspection_date": inspection_date,
                        "source_url": source_url,
                        "content": content[:8000],
                    }).execute()

                    saved += 1
                    logger.info(f"✅ 저장: {company}")
                    time.sleep(0.5)

                except Exception as e:
                    continue

        except Exception as e:
            logger.error(f"{fy_name} 다운로드 실패: {e}")

    logger.info(f"FDA 483 수집 완료 — 총 {saved}건 신규 저장")
    return saved
