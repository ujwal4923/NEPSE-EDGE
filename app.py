
import streamlit as st

st.set_page_config(
    page_title="NEPSE EDGE",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
.block-container {
    padding-top: 1.5rem;
    max-width: 1100px;
}
.main-title {
    font-size: 34px;
    font-weight: 800;
    text-align: center;
    margin-bottom: 0;
}
.sub-title {
    text-align: center;
    color: gray;
    font-size: 14px;
    margin-bottom: 28px;
}
div.stButton > button {
    width: 100%;
    min-height: 115px;
    border-radius: 14px;
    border: 1px solid #777777;
    font-size: 17px;
    font-weight: 700;
    white-space: pre-line;
}
div.stButton > button:hover {
    border: 2px solid #2196F3;
    color: #2196F3;
}
</style>
""", unsafe_allow_html=True)

# PAGE LIST
pages = {
    "📊 Market Dashboard": "Market Dashboard",
    "🔎 Stock Scanner": "Stock Scanner",
    "🏢 Sector Explorer": "Sector Explorer",
    "📚 Fundamental Analysis": "Fundamental Analysis",
    "📈 Technical Analysis": "Technical Analysis",
    "📰 News Intelligence": "News Intelligence",
    "🧠 Smart Recommendations": "Smart Recommendations",
    "💼 Watchlist & Portfolio": "Watchlist & Portfolio"
}

# SESSION
if "page" not in st.session_state:
    st.session_state.page = "Home"

# HEADER
st.markdown(
    '<div class="main-title">📈 NEPSE EDGE</div>',
    unsafe_allow_html=True
)
st.markdown(
    '<div class="sub-title">Nepal Stock Market Intelligence Platform</div>',
    unsafe_allow_html=True
)

# SIDEBAR MENU
with st.sidebar:
    st.markdown("## 📈 NEPSE EDGE")
    st.caption("Navigation Menu")
    st.divider()

    if st.button("🏠 Home", use_container_width=True):
        st.session_state.page = "Home"
        st.rerun()

    for label, page in pages.items():
        if st.button(label, key="menu_" + page):
            st.session_state.page = page
            st.rerun()

# HOME DASHBOARD
if st.session_state.page == "Home":

    st.markdown("### Explore NEPSE")
    st.caption("Select a section to explore.")

    items = list(pages.items())

    for i in range(0, len(items), 2):
        col1, col2 = st.columns(2, gap="medium")

        for col, item in zip(
            [col1, col2],
            items[i:i+2]
        ):
            label, page = item

            with col:
                if st.button(
                    label,
                    key="home_" + page
                ):
                    st.session_state.page = page
                    st.rerun()

# MODULE PAGES
else:
    current_page = st.session_state.page

    st.divider()

    if st.button("⬅ Back to Home"):
        st.session_state.page = "Home"
        st.rerun()

    st.markdown(f"## {current_page}")
    st.divider()

    if current_page == "Market Dashboard":
        st.info("Market Dashboard will be developed here.")

    elif current_page == "Stock Scanner":
        st.info("Stock Scanner will be developed here.")

    elif current_page == "Sector Explorer":
        st.info("Sector Explorer will be developed here.")

    elif current_page == "Fundamental Analysis":
        st.info("Fundamental Analysis will be developed here.")

    elif current_page == "Technical Analysis":
        st.info("Technical Analysis will be developed here.")

    elif current_page == "News Intelligence":
        st.info("News Intelligence will be developed here.")

    elif current_page == "Smart Recommendations":
        st.info("Smart Recommendation Engine will be developed here.")

    elif current_page == "Watchlist & Portfolio":
        st.info("Watchlist & Portfolio will be developed here.")

# FOOTER
st.divider()
st.caption(
    "NEPSE EDGE © 2026 | Independent Stock Market Analysis Platform"
)
