
import streamlit as st
import pandas as pd

# PAGE SETTINGS
st.set_page_config(
    page_title="NEPSE EDGE",
    page_icon="📈",
    layout="wide"
)

# HEADER
st.title("📈 NEPSE EDGE")
st.caption("Smart Stock Analysis & Market Intelligence")

st.info(
    "DEMO MODE: This is the first dashboard. "
    "Live NEPSE data will be connected in the next phase."
)

# SIDEBAR
st.sidebar.title("NEPSE EDGE")
page = st.sidebar.selectbox(
    "Select Module",
    [
        "Dashboard",
        "Stock Scanner",
        "Technical Analysis",
        "Fundamental Analysis",
        "Broker Intelligence",
        "My Portfolio"
    ]
)

st.sidebar.markdown("---")
st.sidebar.caption("Version 1.0 | Development")

# DASHBOARD
if page == "Dashboard":

    st.subheader("Market Overview")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("NEPSE Index", "DEMO", "Not connected")
    col2.metric("Turnover", "DEMO", "Not connected")
    col3.metric("Total Volume", "DEMO", "Not connected")
    col4.metric("Market Status", "Pending", "Data connection")

    st.markdown("---")

    st.subheader("📊 Market Watchlist")

    data = {
        "Symbol": ["SAHAS", "NGPL", "PHCL", "LEC"],
        "Buy Price": [668, 409, 328, 237],
        "Note": [
            "Demo portfolio",
            "Demo portfolio",
            "Demo portfolio",
            "Demo portfolio"
        ]
    }

    df = pd.DataFrame(data)

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    st.subheader("📈 Stock Scanner")

    st.write(
        "Our future scanner will analyze all NEPSE stocks "
        "using trend, momentum, volume and broker activity."
    )

    st.warning(
        "BUY and SELL signals are not active yet. "
        "We will enable them only after connecting and testing real data."
    )

# STOCK SCANNER
elif page == "Stock Scanner":

    st.subheader("🔍 Smart Stock Scanner")

    st.write("Find stocks with strong market potential.")

    st.info("Scanner will be activated after live data integration.")

# TECHNICAL ANALYSIS
elif page == "Technical Analysis":

    st.subheader("📉 Technical Analysis")

    symbol = st.text_input(
        "Enter NEPSE Symbol",
        placeholder="Example: NGPL"
    )

    if st.button("Analyze Stock"):
        if symbol:
            st.info(
                "Technical analysis will be available "
                "after historical price data integration."
            )
        else:
            st.warning("Please enter a stock symbol.")

# FUNDAMENTAL ANALYSIS
elif page == "Fundamental Analysis":

    st.subheader("🏢 Fundamental Analysis")

    st.write("Company financial health and valuation.")

    st.info(
        "EPS, P/E, ROE, debt and quarterly profit "
        "analysis will be added in the next phase."
    )

# BROKER INTELLIGENCE
elif page == "Broker Intelligence":

    st.subheader("🏦 Broker Intelligence")

    st.write("Floorsheet and broker transaction analysis.")

    st.info(
        "Broker-wise net buying, net selling "
        "and accumulation tracking will be added."
    )

# PORTFOLIO
elif page == "My Portfolio":

    st.subheader("💼 My Portfolio")

    st.write("Track your stock investments.")

    st.info(
        "Portfolio profit, loss, average cost "
        "and target tracking will be developed here."
    )

# FOOTER
st.markdown("---")
st.caption(
    "NEPSE EDGE | Personal Stock Research Platform | "
    "Built for data-driven trading"
)
