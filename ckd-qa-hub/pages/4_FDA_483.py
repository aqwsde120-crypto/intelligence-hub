import streamlit as st
from app.database.supabase_client import fetch_fda_483
from app.utils.charts import gmp_area_pie
from app.utils.export import to_excel

st.set_page_config(page_title="FDA 483 | 종근당 QA Hub", layout="wide")
st.title("🔍 FDA 483 분석")

@st.cache_data(ttl=300)
def load():
    return fetch_fda_483(limit=200)

data = load()

with st.expander("🔍 검색 및 필터", expanded=True):
    fc1, fc2 = st.columns(2)
    with fc1:
        query = st.text_input("업체명 검색")
    with fc2:
        risk_filter = st.selectbox("위험도", ["전체", "High", "Medium", "Low"])

filtered = data
if query:
    filtered = [d for d in filtered if query.lower() in d.get("company_name", "").lower()]
if risk_filter != "전체":
    filtered = [
        d for d in filtered
        if ((d.get("ai_analyses") or [{}])[0] if isinstance(d.get("ai_analyses"), list) else (d.get("ai_analyses") or {})).get("risk_level", "").lower() == risk_filter.lower()
    ]

col_info, col_export = st.columns([3, 1])
with col_info:
    st.caption(f"총 {len(filtered)}건")
with col_export:
    if st.button("📥 Excel 내보내기"):
        excel_bytes = to_excel(filtered, "FDA_483")
        st.download_button("⬇️ 다운로드", excel_bytes, "fda_483.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

RISK_COLOR = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}
for item in filtered:
    ai = item.get("ai_analyses") or {}
    if isinstance(ai, list):
        ai = ai[0] if ai else {}

    risk = ai.get("risk_level", "N/A")
    repeated = "🔁 반복 지적" if "반복" in (ai.get("root_cause") or "") else ""
    header = f"{RISK_COLOR.get(risk,'⚪')} **{item.get('company_name','N/A')}** | {item.get('inspection_date','')} {repeated}"

    with st.expander(header):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**📝 주요 Observation 요약**\n\n{ai.get('summary', '-')}")
            st.markdown(f"**📋 GMP 카테고리**\n\n{ai.get('gmp_area', '-')}")
            st.markdown(f"**🔄 반복 지적 여부**\n\n{ai.get('root_cause', '-')}")
        with col2:
            st.markdown(f"**⚠️ 품질 리스크**\n\n{ai.get('lessons_learned', '-')}")
            st.markdown(f"**🏭 종근당 영향도**\n\n{ai.get('ckd_impact', '-')}")
            st.markdown(f"**✅ 권장 조치사항**\n\n{ai.get('recommended_action', '-')}")
        st.markdown(f"[원문 보기]({item.get('source_url','')})")

st.divider()
st.plotly_chart(gmp_area_pie(filtered), use_container_width=True)
