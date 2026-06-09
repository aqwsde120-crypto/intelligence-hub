"""Plotly 차트 유틸리티"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

CKD_BLUE = "#005BAC"
PALETTE = ["#005BAC", "#E8A000", "#D04040", "#2E8B57", "#7B4FBB", "#E85D04", "#0077CC", "#5C4033"]


def risk_heatmap(data: list[dict]) -> go.Figure:
    """GMP 카테고리별 위험도 히트맵"""
    categories = [
        "문서관리", "교육훈련", "일탈관리", "변경관리", "CAPA",
        "데이터완전성", "밸리데이션", "시험실관리", "공급업체관리", "무균보증",
    ]
    sources = ["Warning Letter", "FDA 483", "MFDS 공지"]

    # 데이터에서 카테고리별 빈도 계산
    matrix = {s: {c: 0 for c in categories} for s in sources}
    for item in data:
        ai = item.get("ai_analyses") or {}
        if isinstance(ai, list):
            ai = ai[0] if ai else {}
        gmp_area = ai.get("gmp_area", "") or ""
        src_type = item.get("_source", "Warning Letter")
        for cat in categories:
            if cat.replace(" ", "") in gmp_area.replace(" ", ""):
                matrix[src_type][cat] += 1

    z = [[matrix[s][c] for c in categories] for s in sources]
    fig = go.Figure(go.Heatmap(
        z=z, x=categories, y=sources,
        colorscale=[[0, "#EBF5FB"], [0.5, "#2E86C1"], [1, "#1A5276"]],
        text=[[str(v) if v > 0 else "" for v in row] for row in z],
        texttemplate="%{text}",
        showscale=True,
    ))
    fig.update_layout(
        title="GMP 카테고리별 리스크 히트맵 (최근 3개월)",
        height=280, margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Malgun Gothic, sans-serif"),
    )
    return fig


def monthly_trend(wl_data: list[dict], f483_data: list[dict]) -> go.Figure:
    """월별 이슈 추이 라인 차트"""
    def to_month(items, date_col):
        months: dict[str, int] = {}
        for item in items:
            d = item.get(date_col, "")
            if d and len(d) >= 7:
                m = d[:7]
                months[m] = months.get(m, 0) + 1
        return months

    wl_m = to_month(wl_data, "issued_date")
    f483_m = to_month(f483_data, "inspection_date")
    all_months = sorted(set(list(wl_m.keys()) + list(f483_m.keys())))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=all_months, y=[wl_m.get(m, 0) for m in all_months],
        mode="lines+markers", name="Warning Letter",
        line=dict(color="#D04040", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=all_months, y=[f483_m.get(m, 0) for m in all_months],
        mode="lines+markers", name="FDA 483",
        line=dict(color=CKD_BLUE, width=2),
    ))
    fig.update_layout(
        title="월별 GMP 이슈 추이", height=280,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", y=-0.2),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def country_bar(wl_data: list[dict]) -> go.Figure:
    """국가별 Warning Letter 분포"""
    counts: dict[str, int] = {}
    for item in wl_data:
        c = item.get("country") or "기타"
        counts[c] = counts.get(c, 0) + 1
    df = pd.DataFrame(sorted(counts.items(), key=lambda x: -x[1])[:10], columns=["국가", "건수"])
    fig = px.bar(df, x="건수", y="국가", orientation="h",
                 color_discrete_sequence=[CKD_BLUE])
    fig.update_layout(title="국가별 Warning Letter", height=280,
                      margin=dict(l=10, r=10, t=40, b=10),
                      paper_bgcolor="rgba(0,0,0,0)")
    return fig


def gmp_area_pie(data: list[dict]) -> go.Figure:
    """GMP 영역별 분포 파이 차트"""
    counts: dict[str, int] = {}
    for item in data:
        ai = item.get("ai_analyses") or {}
        if isinstance(ai, list):
            ai = ai[0] if ai else {}
        area = ai.get("gmp_area") or "미분류"
        area = area.split("\n")[0][:20]
        counts[area] = counts.get(area, 0) + 1

    labels = list(counts.keys())[:8]
    values = [counts[l] for l in labels]
    fig = go.Figure(go.Pie(labels=labels, values=values,
                           marker_colors=PALETTE[:len(labels)],
                           hole=0.4))
    fig.update_layout(title="GMP 영역별 분포", height=280,
                      margin=dict(l=10, r=10, t=40, b=10),
                      paper_bgcolor="rgba(0,0,0,0)")
    return fig
