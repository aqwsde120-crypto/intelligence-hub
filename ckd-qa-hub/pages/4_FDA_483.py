import streamlit as st
from app.database.supabase_client import fetch_fda_483
from app.utils.charts import gmp_area_pie
from app.utils.export import to_excel

st.set_page_config(page_title="FDA 483 | 종근당 QA Hub", layout="wide")
st.title("🔍 FDA 483 분석")

# ── 데이터 로드 ───────────────────────────────────────────
@st.cache_data(ttl=300)
def load():
    return fetch_fda_483(limit=200)

data = load()

# ── 필터 ─────────────────────────────────────────────────
with st.expander(":material/filter_list: 검색 및 필터", expanded=True):
    fc1, fc2 = st.columns(2)
    with fc1:
        query = st.text_input("업체명 검색", placeholder="예: Pfizer")
    with fc2:
        risk_filter = st.selectbox("위험도", ["전체", "High", "Medium", "Low"])

# 필터링
filtered = data

if query:
    filtered = [
        d for d in filtered 
        if query.lower() in str(d.get("company_name", "")).lower()
    ]

if risk_filter != "전체":
    filtered = [
        d for d in filtered
        if str(d.get("risk_level") or d.get("ai_risk_level", "")).lower() == risk_filter.lower()
    ]

# ── 내보내기 ─────────────────────────────────────────────
col_info, col_export = st.columns([3, 1])
with col_info:
    st.caption(f"총 **{len(filtered)}건**")

with col_export:
    if st.button(":material/download: Excel 내보내기"):
        with st.spinner("Excel 파일 생성 중..."):
            excel_bytes = to_excel(filtered, "FDA_483")
            st.download_button(
                label="⬇️ 다운로드 시작",
                data=excel_bytes,
                file_name="fda_483.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# ── 목록 ─────────────────────────────────────────────────
RISK_COLOR = {"High": "🔴", "Medium": "🟡", "Low": "🟢", "N/A": "⚪"}

for item in filtered:
    risk = str(item.get("risk_level") or item.get("ai_risk_level", "N/A"))
    icon = RISK_COLOR.get(risk, "⚪")
    
    repeated = " 🔁 반복 지적" if "반복" in str(item.get("root_cause") or "").lower() else ""
    
    header = f"{icon} **{item.get('company_name', 'N/A')}** | {item.get('inspection_date', '')}{repeated}"
    
    with st.expander(header, expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**📝 주요 Observation 요약**\n\n{item.get('summary', '-')}")
            st.markdown(f"**📋 GMP 카테고리**\n\n{item.get('gmp_area', '-')}")
            st.markdown(f"**🔄 반복 지적 여부**\n\n{item.get('root_cause', '-')}")
        with col2:
            st.markdown(f"**⚠️ 품질 리스크**\n\n{item.get('lessons_learned', '-')}")
            st.markdown(f"**🏭 종근당 영향도**\n\n{item.get('ckd_impact', '-')}")
            st.markdown(f"**✅ 권장 조치사항**\n\n{item.get('recommended_action', '-')}")
        
        url = item.get('source_url', '')
        if url:
            st.markdown(f"[📄 원문 보기]({url})")

st.divider()

# ── 차트 ─────────────────────────────────────────────────
st.subheader("📊 GMP 위반 영역 분포")
st.plotly_chart(gmp_area_pie(filtered), use_container_width=True)
