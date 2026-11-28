
import streamlit as st

st.set_page_config(
    page_title="NEPSE EDGE",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------- MOBILE RESPONSIVE DESIGN ----------

st.markdown("""
<style>

/* Main page */
.stApp {
    width: 100%;
}

.block-container {
    max-width: 100% !important;
    padding: 1rem 0.65rem 2rem 0.65rem !important;
}

/* Header */
.edge-header {
    text-align: center;
    padding: 8px 0 20px 0;
}

.edge-logo {
    font-size: 38px;
    font-weight: 900;
    letter-spacing: 2px;
    color: #2196F3;
}

.edge-subtitle {
    font-size: 12px;
    letter-spacing: 1.5px;
    color: #999999;
    margin-top: 4px;
}

/* Section heading */
.section-heading {
    font-size: 19px;
    font-weight: 800;
    margin: 8px 0 14px 3px;
}

/* Force two columns on mobile */
div[data-testid="stHorizontalBlock"] {
    display: flex !important;
    flex-wrap: nowrap !important;
    gap: 10px !important;
    width: 100% !important;
}

div[data-testid="column"] {
    width: 50% !important;
    min-width: 0 !important;
    flex: 1 1 50% !important;
}

/* Equal size dashboard boxes */
div.stButton > button {
    width: 100% !important;
    height: 116px !important;
    min-height: 116px !important;
    max-height: 116px !important;
    border-radius: 16px !important;
    border: 1px solid #64748b !important;
    background: rgba(100, 116, 139, 0.09) !important;
    font-size: 15px !important;
    font-weight: 800 !important;
    line-height: 1.5 !important;
    white-space: pre-line !important;
    text-align: center !important;
    padding: 8px 3px !important;
    overflow-wrap: anywhere !important;
    box-shadow: 0 3px 10px rgba(0,0,0,0.08);
}

/* Hover and touch */
div.stButton > button:hover {
    border: 2px solid #2196F3 !important;
    color: #2196F3 !important;
    transform: translateY(-2px);
}

/* Footer */
.edge-footer {
    text-align: center;
    font-size: 11px;
    color: #888888;
    padding: 20px 0;
}

/* Small mobile screens */
@media (max-width: 380px) {
    .block-container {
        padding-left: 0.4rem !important;
        padding-right: 0.4rem !important;
    }

    div[data-testid="stHorizontalBlock"] {
        gap: 7px !important;
    }

    div.stButton > button {
        height: 108px !important;
        min-height: 108px !important;
        max-height: 108px !important;
        font-size: 13px !important;
    }

    .edge-logo {
        font-size: 32px;
    }
}

</style>
""", unsafe_allow_html=True)


# ---------- NAVIGATION ----------

pages = [
    ("📊\nMARKET DASHBOARD", "Market Dashboard"),
    ("🔍\nSTOCK SCANNER", "Stock Scanner"),
    ("🏢\nSECTOR EXPLORER", "Sector Explorer"),
    ("📚\nFUNDAMENTAL ANALYSIS", "Fundamental Analysis"),
    ("📈\nTECHNICAL ANALYSIS", "Technical Analysis"),
    ("📰\nNEWS INTELLIGENCE", "News Intelligence"),
    ("🧠\nSMART RECOMMENDATIONS", "Smart Recommendations"),
    ("💼\nWATCHLIST & PORTFOLIO", "Watchlist & Portfolio")
]

if "page" not in st.session_state:
    st.session_state.page = "Home"


# ---------- HEADER ----------

st.markdown("""
<div class="edge-header">
    <div class="edge-logo">📈 NEPSE EDGE</div>
    <div class="edge-subtitle">
        NEPAL STOCK MARKET INTELLIGENCE
    </div>
</div>
""", unsafe_allow_html=True)


# ---------- MENU ----------

with st.sidebar:

    st.markdown("## 📈 NEPSE EDGE")
    st.caption("MAIN NAVIGATION")
    st.divider()

    if st.button("🏠 HOME", use_container_width=True):
        st.session_state.page = "Home"
        st.rerun()

    for label, page in pages:
        if st.button(label, key="menu_" + page,
                     use_container_width=True):
            st.session_state.page = page
            st.rerun()


# ---------- HOME DASHBOARD ----------

if st.session_state.page == "Home":

    st.markdown(
        '<div class="section-heading">EXPLORE NEPSE</div>',
        unsafe_allow_html=True
    )

    for i in range(0, len(pages), 2):

        left, right = st.columns(2, gap="small")

        for col, item in zip(
            [left, right],
            pages[i:i+2]
        ):

            label, page = item

            with col:
                if st.button(
                    label,
                    key="home_" + page,
                    use_container_width=True
                ):
                    st.session_state.page = page
                    st.rerun()


# ---------- MODULE PAGES ----------

else:

    current_page = st.session_state.page

    st.divider()

    if st.button("⬅ HOME", key="back_home"):
        st.session_state.page = "Home"
        st.rerun()

    st.markdown(f"## {current_page}")

    st.divider()

    if current_page == "Market Dashboard":
        st.info("Market Dashboard module coming soon.")

    elif current_page == "Stock Scanner":
        st.info("Stock Scanner module coming soon.")

    elif current_page == "Sector Explorer":
        st.info("Sector Explorer module coming soon.")

    elif current_page == "Fundamental Analysis":
        st.info("Fundamental Analysis module coming soon.")

    elif current_page == "Technical Analysis":
        st.info("Technical Analysis module coming soon.")

    elif current_page == "News Intelligence":
        st.info("News Intelligence module coming soon.")

    elif current_page == "Smart Recommendations":
        st.info("Smart Recommendation Engine coming soon.")

    elif current_page == "Watchlist & Portfolio":
        st.info("Watchlist & Portfolio module coming soon.")


# ---------- FOOTER ----------

st.markdown("""
<div class="edge-footer">
    NEPSE EDGE © 2026<br>
    INDEPENDENT STOCK MARKET INTELLIGENCE PLATFORM
</div>
""", unsafe_allow_html=True)
