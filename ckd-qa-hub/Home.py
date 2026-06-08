import streamlit as st

st.set_page_config(
    page_title="종근당 QA Intelligence Hub",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #003B75; }
    [data-testid="stSidebar"] * { color: white !important; }
    .stMetric { background: #F0F4F8; border-radius: 10px; padding: 12px; }
    .risk-high { color: #C0392B; font-weight: bold; }
    .risk-medium { color: #E67E22; font-weight: bold; }
    .risk-low { color: #27AE60; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("💊 종근당 QA Intelligence Hub")
st.markdown("**AI 기반 품질 인텔리전스 플랫폼** | 왼쪽 메뉴에서 기능을 선택하세요.")

col1, col2, col3 = st.columns(3)
with col1:
    st.info("📋 **GMP 규제 동향**\nFDA · EMA · MFDS 최신 규제")
with col2:
    st.warning("⚠️ **Warning Letter / FDA 483**\nAI 심층 분석 및 종근당 영향도")
with col3:
    st.error("🔍 **데이터 완전성 모니터링**\nALCOA+ 기반 자동 분류")
