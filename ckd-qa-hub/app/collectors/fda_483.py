import time
import logging
import requests
import pandas as pd
from datetime import datetime
from app.database.supabase_client import get_client

logger = logging.getLogger(__name__)

# 최신 FY Excel 다운로드 링크 (FDA 공식)
EXCEL_URLS = {
    "FY2025": "https://www.fda.gov/media/190190/download",
    "FY2024": "https://www.fda.gov/media/185090/download",
    "FY2023": "https://www.fda.gov/media/174101/download",
    "FY2022": "https://www.fda.gov/media/163420/download",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CKD-QA-Hub/1.0)"
}


def collect() -> int:
    """FDA 483 Excel 파일에서 데이터 수집"""
    db = get_client()
    saved = 0

    for fy_name, url in EXCEL_URLS.items():
        logger.info(f"📥 {fy_name} Excel 다운로드 중...")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=60)
            resp.raise_for_status()

            # Excel 읽기
            df = pd.read_excel(resp.content, engine="openpyxl")
            logger.info(f"{fy_name} 로드 완료: {len(df)} rows, 컬럼: {list(df.columns)}")

            for _, row in df.iterrows():
                try:
                    # 회사명 찾기 (컬럼명 변동 가능성 대응)
                    company = None
                    for col in ["Firm Name", "Company Name", "Name", "firm_name"]:
                        if col in df.columns and pd.notna(row[col]):
                            company = str(row[col]).strip()
                            break
                    if not company or len(company) < 3:
                        continue

                    # 검사 날짜
                    inspection_date = datetime.now().date().isoformat()
                    for col in ["Inspection Date", "Date", "inspection_date", "Date of Inspection"]:
                        if col in df.columns and pd.notna(row[col]):
                            try:
                                inspection_date = pd.to_datetime(row[col]).date().isoformat()
                                break
                            except:
                                continue

                    source_url = ""

                    # 중복 체크
                    existing = (
                        db.table("fda_483")
                        .select("id")
                        .eq("company_name", company)
                        .eq("inspection_date", inspection_date)
                        .execute()
                    )
                    if existing.data:
                        continue

                    # content 생성
                    content_parts = [f"Fiscal Year: {fy_name}"]
                    for col in df.columns[:15]:  # 주요 컬럼만
                        if pd.notna(row[col]):
                            content_parts.append(f"{col}: {row[col]}")

                    content = "\n".join(content_parts)

                    db.table("fda_483").insert({
                        "company_name": company,
                        "inspection_date": inspection_date,
                        "source_url": source_url,
                        "content": content[:8000],
                    }).execute()

                    saved += 1
                    logger.info(f"✅ 저장: {company}")
                    time.sleep(0.4)

                except Exception as inner_e:
                    continue

        except Exception as e:
            logger.error(f"{fy_name} 처리 실패: {e}")

    logger.info(f"🎉 FDA 483 수집 완료 — 총 {saved}건 신규 저장")
    return saved
