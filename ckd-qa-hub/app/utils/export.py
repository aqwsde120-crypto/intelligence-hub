import io
import pandas as pd

def _get_ai(item: dict, field: str, default=""):
    ai = item.get("ai_analyses") or {}
    if isinstance(ai, list) and ai:
        ai = ai[0]
    return ai.get(field) if isinstance(ai, dict) else item.get(field, default)


def to_excel(data: list[dict], sheet_name: str = "데이터") -> bytes:
    rows = []
    for item in data:
        row = {
            "업체명": item.get("company_name") or item.get("title", ""),
            "국가": item.get("country", ""),
            "날짜": item.get("issued_date") or item.get("inspection_date") or item.get("published_date", ""),
            "AI 요약": _get_ai(item, "summary"),
            "GMP 영역": _get_ai(item, "gmp_area"),
            "위험도": _get_ai(item, "risk_level"),
            "종근당 영향도": _get_ai(item, "ckd_impact"),
            "권장 조치": _get_ai(item, "recommended_action"),
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
