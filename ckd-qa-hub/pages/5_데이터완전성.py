import streamlit as st
from app.database.supabase_client import get_client

st.set_page_config(page_title="데이터 완전성 | 종근당 QA Hub", layout="wide")
st.title("🔒 ALCOA+ 데이터 완전성 모니터링")
st.caption("Warning Letter 및 FDA 483 AI 자동 분류 기반")

ALCOA_ITEMS = [
    ("Attributable", "귀속성", "데이터 작성자·시스템이 명확히 식별되는가"),
    ("Legible", "판독성", "데이터가 영구적으로 판독 가능한가"),
    ("Contemporaneous", "동시성", "활동 발생 시점에 즉시 기록되었는가"),
    ("Original", "원본성", "원본 또는 진본 사본이 보존되는가"),
    ("Accurate", "정확성", "오류 없이 정확하게 기록되었는가"),
    ("Complete", "완전성", "모든 데이터가 누락 없이 기록되었는가"),
    ("Consistent", "일관성", "날짜·버전·단위가 일관되게 사용되는가"),
    ("Enduring", "내구성", "저장 매체가 기록 보존 기간을 지원하는가"),
    ("Available", "가용성", "검토·감사 시 데이터에 접근 가능한가"),
]

# 탭
tab1, tab2 = st.tabs([":material/menu_book: ALCOA+ 항목 현황", ":material/search: 위반 사례 분석"])

with tab1:
    db = get_client()
    try:
        analyses = (
            db.table("ai_analyses")
            .select("alcoa_category, source_type, risk_level")
            .not_.is_("alcoa_category", "null")
            .execute()
            .data
        )
    except Exception as e:
        st.error("데이터 조회 중 오류가 발생했습니다.")
        st.stop()

    # 항목별 집계
    counts: dict[str, int] = {name: 0 for name, _, _ in ALCOA_ITEMS}
    for row in analyses:
        cat = str(row.get("alcoa_category", "")).lower()
        for name, _, _ in ALCOA_ITEMS:
            if name.lower() in cat:
                counts[name] += 1

    cols = st.columns(3)
    for i, (name, kor, desc) in enumerate(ALCOA_ITEMS):
        with cols[i % 3]:
            cnt = counts.get(name, 0)
            color = "#D04040" if cnt >= 3 else "#E67E22" if cnt >= 1 else "#27AE60"
            
            st.markdown(f"""
            <div style="border:1px solid {color}; border-radius:8px; padding:16px; margin-bottom:12px; background-color:#f8f9fa;">
                <b style="color:{color};">{name}</b> ({kor})<br>
                <small style="color:#555;">{desc}</small><br><br>
                <b style="font-size:28px; color:{color};">{cnt}</b>건
            </div>
            """, unsafe_allow_html=True)

with tab2:
    db = get_client()
    try:
        di_cases = (
            db.table("ai_analyses")
            .select("""
                source_type, source_id, summary, root_cause, 
                ckd_impact, recommended_action, alcoa_category, risk_level
            """)
            .not_.is_("alcoa_category", "null")
            .neq("alcoa_category", "해당없음")
            .order("risk_level", desc=True)
            .execute()
            .data
        )
    except Exception as e:
        st.error("사례 조회 중 오류가 발생했습니다.")
        di_cases = []

    if not di_cases:
        st.info("현재 ALCOA+ 위반 사례로 분류된 데이터가 없습니다.")
    else:
        for case in di_cases:
            risk = case.get("risk_level", "")
            icon = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(risk, "⚪")
            
            header = f"{icon} [{case.get('source_type','').upper()}] ALCOA: {case.get('alcoa_category','N/A')}"
            
            with st.expander(header, expanded=False):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**📝 사례 요약**\n\n{case.get('summary', '-')}")
                    st.markdown(f"**🔍 Root Cause**\n\n{case.get('root_cause', '-')}")
                with c2:
                    st.markdown(f"**🏭 종근당 영향도**\n\n{case.get('ckd_impact', '-')}")
                    st.markdown(f"**✅ 권장 조치사항**\n\n{case.get('recommended_action', '-')}")

st.divider()
st.caption("※ ALCOA+ 분류는 AI 분석 결과에 기반하며, 수동 검토가 필요합니다.")
