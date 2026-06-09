import streamlit as st
from app.database.supabase_client import fetch_warning_letters
from app.utils.charts import gmp_area_pie, country_bar
from app.utils.export import to_excel

st.set_page_config(page_title="Warning Letter | 종근당 QA Hub", layout="wide")
st.title("⚠️ Warning Letter 분석")

# ── 데이터 로드 (Warning Letter 전용) ─────────────────────────────────
@st.cache_data(ttl=300)
def load():
    return fetch_warning_letters(limit=200)

data = load()

st.caption(f"Warning Letter 총 **{len(data)}건** 로드됨")

# ── 필터 ─────────────────────────────────────────────────
with st.expander(":material/filter_list: 검색 및 필터", expanded=True):
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        query = st.text_input("업체명 / 국가 검색", placeholder="예: Pfizer, Korea")
    with fc2:
        risk_filter = st.selectbox("위험도", ["전체", "High", "Medium", "Low"])
    with fc3:
        sort_by = st.selectbox("정렬", ["최신순", "위험도순"])

# 필터링
filtered = data

if query:
    filtered = [
        d for d in filtered 
        if query.lower() in str(d.get("company_name", "") + " " + d.get("country", "")).lower()
    ]

if risk_filter != "전체":
    filtered = [
        d for d in filtered
        if str(d.get("risk_level") or d.get("ai_risk_level", "")).lower() == risk_filter.lower()
    ]

if sort_by == "위험도순":
    order = {"high": 0, "medium": 1, "low": 2}
    filtered.sort(key=lambda x: order.get(str(x.get("risk_level") or x.get("ai_risk_level", "low")).lower(), 3))

# ── 내보내기 ─────────────────────────────────────────────
col_info, col_export = st.columns([3, 1])
with col_info:
    st.caption(f"필터 적용 후 **{len(filtered)}건**")

with col_export:
    if st.button(":material/download: Excel 내보내기"):
        with st.spinner("Excel 생성 중..."):
            excel_bytes = to_excel(filtered, "Warning_Letters")
            st.download_button("⬇️ 다운로드", excel_bytes, "warning_letters.xlsx", 
                             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ── 목록 표시 ─────────────────────────────────────────────
RISK_COLOR = {"High": "🔴", "Medium": "🟡", "Low": "🟢", "N/A": "⚪"}

for item in filtered:
    risk = str(item.get("risk_level") or item.get("ai_risk_level", "N/A"))
    icon = RISK_COLOR.get(risk, "⚪")
    
    header = f"{icon} **{item.get('company_name', 'N/A')}** | {item.get('country', 'N/A')} | {item.get('issued_date', '')}"
    
    with st.expander(header, expanded=False):
        t1, t2 = st.tabs(["🤖 AI 분석", "📄 원문 정보"])
        with t1:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**📝 AI 요약**\n\n{item.get('summary', '분석 데이터 없음')}")
                st.markdown(f"**🔍 Root Cause**\n\n{item.get('root_cause', '-')}")
                st.markdown(f"**📋 GMP 위반 영역**\n\n{item.get('gmp_area', '-')}")
            with col2:
                st.markdown(f"**💡 Lessons Learned**\n\n{item.get('lessons_learned', '-')}")
                st.markdown(f"**🏭 종근당 영향도**\n\n{item.get('ckd_impact', '-')}")
                st.markdown(f"**✅ 권장 조치사항**\n\n{item.get('recommended_action', '-')}")
        with t2:
            url = item.get('source_url', '')
            if url:
                st.markdown(f"[원문 링크]({url})")
            if item.get("content"):
                st.text_area("원문", item["content"][:1500], height=300, disabled=True)

st.divider()

# 차트
st.subheader("📊 분포 분석")
cc1, cc2 = st.columns(2)
with cc1:
    st.plotly_chart(gmp_area_pie(filtered), use_container_width=True)
with cc2:
    st.plotly_chart(country_bar(filtered), use_container_width=True)
