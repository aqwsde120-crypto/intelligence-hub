import streamlit as st
import pandas as pd
from datetime import date, timedelta
from app.database.supabase_client import (
    fetch_warning_letters, fetch_fda_483, fetch_mfds_notices,
    fetch_weekly_briefing, count_new_this_week,
)
from app.utils.charts import risk_heatmap, monthly_trend, country_bar

st.set_page_config(page_title="대시보드 | 종근당 QA Hub", layout="wide")
st.title("📊 대시보드")

# ── KPI 카드 ──────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    n = count_new_this_week("warning_letters", "issued_date")
    st.metric("신규 Warning Letter", n, delta="이번 주")
with c2:
    n = count_new_this_week("fda_483", "inspection_date")
    st.metric("신규 FDA 483", n, delta="이번 주")
with c3:
    n = count_new_this_week("mfds_notices", "published_date")
    st.metric("신규 MFDS 공지", n, delta="이번 주")
with c4:
    wl_data = fetch_warning_letters(limit=50)
    high_risk = sum(
        1 for w in wl_data
        if (w.get("ai_analyses") or [{}])[0].get("risk_level", "").lower() == "high"
    )
    st.metric("고위험 항목", high_risk, delta="전체 누적")

st.divider()

# ── 주간 브리핑 ───────────────────────────────────────────
today = date.today()
week_start = (today - timedelta(days=today.weekday())).isoformat()
briefing = fetch_weekly_briefing(week_start)

col_brief, col_chart = st.columns([1.2, 1])

with col_brief:
    st.subheader("📋 이번 주 QA 브리핑")
    if briefing and briefing.get("briefing_content"):
        st.markdown(briefing["briefing_content"])
    else:
        st.info("이번 주 브리핑이 아직 생성되지 않았습니다. 월요일 오전 6시 자동 생성됩니다.")
        if st.button("지금 생성하기"):
            with st.spinner("Gemini AI가 브리핑을 생성 중입니다..."):
                from app.ai.weekly_briefing import generate
                content = generate()
                st.success("브리핑 생성 완료!")
                st.markdown(content)

with col_chart:
    st.subheader("🌡️ 글로벌 GMP 리스크 히트맵")
    all_data = [{"_source": "Warning Letter", **w} for w in wl_data]
    all_data += [{"_source": "FDA 483", **f} for f in fetch_fda_483(limit=50)]
    fig = risk_heatmap(all_data)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── 차트 행 ───────────────────────────────────────────────
c1, c2 = st.columns(2)
with c1:
    f483_data = fetch_fda_483(limit=100)
    fig = monthly_trend(wl_data, f483_data)
    st.plotly_chart(fig, use_container_width=True)
with c2:
    fig = country_bar(wl_data)
    st.plotly_chart(fig, use_container_width=True)
