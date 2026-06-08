"""Excel / PDF 내보내기"""

import io
import pandas as pd


def to_excel(data: list[dict], sheet_name: str = "데이터") -> bytes:
    """데이터를 Excel 바이트로 변환"""
    rows = []
    for item in data:
        ai = item.get("ai_analyses") or {}
        if isinstance(ai, list):
            ai = ai[0] if ai else {}
        row = {
            "업체명": item.get("company_name") or item.get("title", ""),
            "국가": item.get("country", ""),
            "날짜": item.get("issued_date") or item.get("inspection_date") or item.get("published_date", ""),
            "AI 요약": ai.get("summary", ""),
            "GMP 영역": ai.get("gmp_area", ""),
            "위험도": ai.get("risk_level", ""),
            "종근당 영향도": ai.get("ckd_impact", ""),
            "권장 조치": ai.get("recommended_action", ""),
            "원문 링크": item.get("source_url", ""),
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        ws = writer.sheets[sheet_name]
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 60)
    return buf.getvalue()
