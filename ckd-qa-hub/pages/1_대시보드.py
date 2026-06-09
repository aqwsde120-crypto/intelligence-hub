import streamlit as st
from datetime import date, timedelta
from app.database.supabase_client import (
    fetch_warning_letters, fetch_fda_483, fetch_mfds_notices,
    fetch_weekly_briefing, count_new_this_week,
)
from app.utils.charts import risk_heatmap, monthly_trend, country_bar

st.set_page_config(page_title="대시보드 | 종근당 QA Hub", layout="wide")
st.title("📊 대시보드")

# ==================== KPI ====================
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
    high_risk = sum(1 for w in wl_data if str(w.get("risk_level", "")).lower() == "high")
    st.metric("고위험 항목", high_risk, delta="전체 누적")

st.divider()

# ==================== 주간 브리핑 + 히트맵 ====================
today = date.today()
week_start = (today - timedelta(days=today.weekday())).isoformat()
briefing = fetch_weekly_briefing(week_start)

col_brief, col_chart = st.columns([1.2, 1])

with col_brief:
    st.subheader("📋 이번 주 QA 브리핑")
    if briefing and briefing.get("briefing_content"):
        st.markdown(briefing["briefing_content"])
    else:
        st.info("이번 주 브리핑이 아직 생성되지 않았습니다. (월요일 자동 생성)")
        if st.button("🪄 지금 브리핑 생성하기"):
            with st.spinner("Gemini AI가 브리핑을 생성 중입니다..."):
                from app.ai.weekly_briefing import generate
                content = generate()
                st.success("브리핑 생성 완료!")
                st.rerun()

with col_chart:
    st.subheader("🌡️ 글로벌 GMP 리스크 히트맵")
    fda_data = fetch_fda_483(limit=30)
    all_data = [{"_source": "Warning Letter", **w} for w in wl_data]
    all_data += [{"_source": "FDA 483", **f} for f in fda_data]
    try:
        fig = risk_heatmap(all_data)
        st.plotly_chart(fig, use_container_width=True)
    except:
        st.info("데이터가 충분하지 않습니다.")

st.divider()

# ==================== 수동 데이터 수집 (강화) ====================
st.subheader("🔄 수동 데이터 수집")

col_a, col_b = st.columns(2)

with col_a:
    if st.button("📥 Warning Letter + FDA 483 + MFDS 수집", type="primary", use_container_width=True):
        with st.spinner("데이터 수집 중... (최대 1~2분 소요)"):
            try:
                from app.collectors.fda_warning_letters import collect as collect_wl
                from app.collectors.fda_483 import collect as collect_483
                from app.collectors.mfds_notices import collect as collect_mfds

                wl_count = collect_wl(max_items=30)
                f483_count = collect_483(max_pages=3)
                mfds_count = collect_mfds(max_pages=2)

                st.success(f"""
                ✅ 수집 완료!
                - Warning Letter : {wl_count}건
                - FDA 483 : {f483_count}건
                - MFDS 공지 : {mfds_count}건
                """)
                st.rerun()
            except Exception as e:
                st.error(f"수집 중 오류 발생: {e}")

with col_b:
    if st.button("🤖 AI 분석 실행 (미분석 데이터만)", type="secondary", use_container_width=True):
        with st.spinner("AI 분석 중... (건수에 따라 시간이 걸릴 수 있습니다)"):
            try:
                from app.ai.gemini_analyzer import run_all_analyses
                analyzed = run_all_analyses()
                st.success(f"✅ AI 분석 완료: {analyzed}건")
                st.rerun()
            except Exception as e:
                st.error(f"AI 분석 오류: {e}")

st.divider()

# ==================== 기존 차트 ====================
c1, c2 = st.columns(2)
with c1:
    wl_data_full = fetch_warning_letters(limit=100)
    f483_data = fetch_fda_483(limit=100)
    fig = monthly_trend(wl_data_full, f483_data)
    st.plotly_chart(fig, use_container_width=True)

with c2:
    fig = country_bar(wl_data_full)
    st.plotly_chart(fig, use_container_width=True)
