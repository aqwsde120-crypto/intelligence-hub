import streamlit as st
from datetime import date, timedelta

from app.database.supabase_client import (
    fetch_warning_letters,
    fetch_fda_483,
    fetch_mfds_notices,
    fetch_weekly_briefing,
    count_new_this_week,
)

from app.utils.charts import (
    risk_heatmap,
    monthly_trend,
    country_bar,
)

st.set_page_config(
    page_title="대시보드 | 종근당 QA Hub",
    layout="wide"
)

st.title("📊 종근당 QA Intelligence Hub")

# ==================================================
# KPI
# ==================================================

c1, c2, c3, c4 = st.columns(4)

with c1:
    wl_new = count_new_this_week(
        "warning_letters",
        "issued_date"
    )

    st.metric(
        "신규 Warning Letter",
        wl_new
    )

with c2:
    f483_new = count_new_this_week(
        "fda_483",
        "inspection_date"
    )

    st.metric(
        "신규 FDA 483",
        f483_new
    )

with c3:
    mfds_new = count_new_this_week(
        "mfds_notices",
        "published_date"
    )

    st.metric(
        "신규 MFDS 공지",
        mfds_new
    )

with c4:

    wl_data = fetch_warning_letters(
        limit=100
    )

    high_risk = sum(
        1
        for w in wl_data
        if (
            (w.get("ai_analyses") or [{}])[0]
            .get("risk_level", "")
            .lower()
            == "high"
        )
    )

    st.metric(
        "고위험 항목",
        high_risk
    )

st.divider()

# ==================================================
# 주간 브리핑
# ==================================================

today = date.today()

week_start = (
    today - timedelta(days=today.weekday())
).isoformat()

briefing = fetch_weekly_briefing(
    week_start
)

left, right = st.columns([1.3, 1])

with left:

    st.subheader(
        "📋 이번 주 QA 브리핑"
    )

    if (
        briefing
        and briefing.get(
            "briefing_content"
        )
    ):

        st.markdown(
            briefing["briefing_content"]
        )

    else:

        st.info(
            "이번 주 브리핑이 없습니다."
        )

        if st.button(
            "브리핑 생성"
        ):

            try:

                from app.ai.weekly_briefing import generate

                with st.spinner(
                    "Gemini 분석 중..."
                ):

                    content = generate()

                st.success(
                    "생성 완료"
                )

                st.markdown(
                    content
                )

            except Exception as e:

                st.error(str(e))

with right:

    st.subheader(
        "🌡️ GMP Risk Heatmap"
    )

    try:

        all_data = [
            {
                "_source": "Warning Letter",
                **x,
            }
            for x in wl_data
        ]

        all_data += [
            {
                "_source": "FDA 483",
                **x,
            }
            for x in fetch_fda_483(
                limit=100
            )
        ]

        fig = risk_heatmap(
            all_data
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    except Exception as e:

        st.warning(
            f"Heatmap 생성 실패: {e}"
        )

st.divider()

# ==================================================
# 트렌드 차트
# ==================================================

c1, c2 = st.columns(2)

with c1:

    try:

        f483_data = fetch_fda_483(
            limit=100
        )

        fig = monthly_trend(
            wl_data,
            f483_data
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    except Exception as e:

        st.warning(
            f"Trend 생성 실패: {e}"
        )

with c2:

    try:

        fig = country_bar(
            wl_data
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    except Exception as e:

        st.warning(
            f"Country Chart 생성 실패: {e}"
        )

st.divider()

# ==================================================
# 데이터 현황
# ==================================================

st.subheader(
    "📂 데이터 현황"
)

st.write(
    "Warning Letter:",
    len(
        fetch_warning_letters(
            limit=1000
        )
    )
)

st.write(
    "FDA 483:",
    len(
        fetch_fda_483(
            limit=1000
        )
    )
)

st.write(
    "MFDS:",
    len(
        fetch_mfds_notices(
            limit=1000
        )
    )
)

st.divider()

# ==================================================
# 데이터 수집
# ==================================================

st.subheader("🔄 데이터 수집")

if st.button("FDA / MFDS 데이터 수집 실행"):

    try:

        from app.collectors.fda_warning_letters import collect as collect_wl
        from app.collectors.fda_483 import collect as collect_483
        from app.collectors.mfds_notices import collect as collect_mfds

        with st.spinner("데이터 수집 중..."):

            st.write("===== Warning Letter 수집 시작 =====")

            wl_count = collect_wl(max_items=50)

            st.success(
                f"Warning Letter 수집 결과 : {wl_count}"
            )

            st.write("===== FDA 483 수집 시작 =====")

            f483_count = collect_483(max_pages=3)

            st.success(
                f"FDA 483 수집 결과 : {f483_count}"
            )

            st.write("===== MFDS 수집 시작 =====")

            mfds_count = collect_mfds(max_pages=2)

            st.success(
                f"MFDS 수집 결과 : {mfds_count}"
            )

        st.success(
            f"""
수집 완료

Warning Letter : {wl_count}
FDA 483 : {f483_count}
MFDS : {mfds_count}
"""
        )

    except Exception as e:

        import traceback

        st.error(str(e))
        st.code(traceback.format_exc())

# ==================================================
# AI 분석
# ==================================================

if st.button(
    "데이터 수집 + AI 분석 실행"
):

    try:

        from app.collectors.fda_warning_letters import collect as collect_wl
        from app.collectors.fda_483 import collect as collect_483
        from app.collectors.mfds_notices import collect as collect_mfds
        from app.ai.gemini_analyzer import run_all_analyses

        with st.spinner(
            "AI 분석 중..."
        ):

            wl_count = collect_wl(
                max_items=50
            )

            f483_count = collect_483(
                max_pages=3
            )

            mfds_count = collect_mfds(
                max_pages=2
            )

            analyzed = run_all_analyses()

        st.success(
            f"""
수집 완료

Warning Letter : {wl_count}
FDA 483 : {f483_count}
MFDS : {mfds_count}
AI 분석 : {analyzed}
"""
        )

    except Exception as e:

        import traceback

        st.error(str(e))

        st.code(
            traceback.format_exc()
        )
