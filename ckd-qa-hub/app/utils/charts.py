# app/utils/charts.py  (전체 교체 추천)
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

CKD_BLUE = "#005BAC"
PALETTE = ["#005BAC", "#E8A000", "#D04040", "#2E8B57", "#7B4FBB", "#E85D04", "#0077CC", "#5C4033"]

def _get_ai_field(item: dict, field: str, default=""):
    """ai_analyses 중첩 구조와 평탄화 구조 모두 지원"""
    ai = item.get("ai_analyses") or {}
    if isinstance(ai, list):
        ai = ai[0] if ai else {}
    return ai.get(field) or item.get(field) or default

def risk_heatmap(data: list[dict]) -> go.Figure:
    categories = ["문서관리", "교육훈련", "일탈관리", "변경관리", "CAPA", "데이터완전성", 
                  "밸리데이션", "시험실관리", "공급업체관리", "무균보증"]
    # ... (기존 로직 유지하되 _get_ai_field 사용)
    matrix = {s: {c: 0 for c in categories} for s in ["Warning Letter", "FDA 483"]}
    for item in data:
        gmp_area = _get_ai_field(item, "gmp_area", "")
        src = item.get("_source", "Warning Letter")
        for cat in categories:
            if cat.replace(" ", "") in gmp_area.replace(" ", ""):
                matrix[src][cat] += 1
    # ... (나머지 heatmap 로직 동일)
    # (전체 코드는 이전 응답 참고)

# monthly_trend, country_bar, gmp_area_pie 도 동일하게 _get_ai_field 적용
