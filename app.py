
import streamlit as st
import pandas as pd
import urllib.request
import json

# ============================================================
# NEPSE EDGE | COMPLETE APP
# Original mobile home design preserved
# ============================================================

st.set_page_config(
    page_title="NEPSE EDGE",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

BASE = "https://raw.githubusercontent.com/Shubhamnpk/yonepse/main/data"

# ============================================================
# ORIGINAL HOME DESIGN - PRESERVED
# ============================================================

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

/* Additional content styling - does not change home boxes */
.edge-card {
    background: rgba(100,116,139,0.10);
    border: 1px solid #64748b;
    border-radius: 13px;
    padding: 13px;
    margin-bottom: 10px;
}

.edge-positive {
    color: #16a34a;
    font-weight: 700;
}

.edge-negative {
    color: #ef4444;
    font-weight: 700;
}

.edge-muted {
    color: #94a3b8;
    font-size: 12px;
}

.edge-heading {
    font-size: 19px;
    font-weight: 800;
    margin-top: 18px;
    margin-bottom: 10px;
}

</style>
""", unsafe_allow_html=True)

# ============================================================
# MODULES - ORIGINAL TITLES PRESERVED
# ============================================================

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

# ============================================================
# DATA FUNCTIONS
# ============================================================

def fetch_json(path):
    url = BASE + "/" + path

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "NEPSE-EDGE"}
    )

    with urllib.request.urlopen(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


@st.cache_data(ttl=300)
def load_market():
    return pd.DataFrame(fetch_json("nepse_data.json"))


@st.cache_data(ttl=300)
def load_indices():
    return pd.DataFrame(fetch_json("market/indices.json"))


@st.cache_data(ttl=300)
def load_summary():
    return pd.DataFrame(fetch_json("market/summary.json"))


@st.cache_data(ttl=300)
def load_securities():
    return pd.DataFrame(fetch_json("other/securities.json"))


@st.cache_data(ttl=300)
def load_top_stocks():
    return fetch_json("market/top_stocks.json")


def prepare_market():
    market = load_market()
    securities = load_securities()

    numeric = [
        "ltp", "previous_close", "change",
        "percent_change", "high", "low",
        "volume", "turnover", "trades", "market_cap"
    ]

    for col in numeric:
        if col in market.columns:
            market[col] = pd.to_numeric(
                market[col], errors="coerce"
            )

    if "symbol" in securities.columns:
        selected = [
            c for c in [
                "symbol", "sectorName",
                "instrumentType", "status",
                "companyName", "securityName"
            ]
            if c in securities.columns
        ]

        securities = securities[selected].drop_duplicates("symbol")

        market = market.merge(
            securities,
            on="symbol",
            how="left"
        )

    if "sectorName" not in market.columns:
        market["sectorName"] = "Unclassified"

    market["sectorName"] = market["sectorName"].fillna("Unclassified")

    if "instrumentType" in market.columns:
        equity = market[
            market["instrumentType"].astype(str).str.lower() == "equity"
        ]
    else:
        equity = market.copy()

    if "status" in equity.columns:
        active = equity[
            equity["status"].astype(str).str.upper() == "A"
        ]
        if not active.empty:
            equity = active

    equity = equity.drop_duplicates("symbol").copy()

    return market, equity


def safe_num(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def fmt(value):
    return f"{safe_num(value):,.2f}"


def compact(value):
    value = safe_num(value)

    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f} B"

    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f} M"

    if abs(value) >= 1_000:
        return f"{value / 1_000:,.2f} K"

    return f"{value:,.2f}"


def money(value):
    return "Rs. " + compact(value)


def summary_value(summary, keyword):
    if summary.empty or "detail" not in summary.columns:
        return None

    found = summary[
        summary["detail"].astype(str).str.contains(
            keyword, case=False, na=False
        )
    ]

    if found.empty:
        return None

    return safe_num(found.iloc[0].get("value"))


def get_index(indices, name):
    if indices.empty or "index" not in indices.columns:
        return None

    found = indices[
        indices["index"].astype(str).str.lower() == name.lower()
    ]

    if found.empty:
        return None

    return found.iloc[0]


def show_table(data, columns, height=350):
    if data is None or data.empty:
        st.info("Data is currently unavailable.")
        return

    available = [c for c in columns if c in data.columns]

    if not available:
        st.info("Requested information is unavailable.")
        return

    st.dataframe(
        data[available],
        use_container_width=True,
        hide_index=True,
        height=height
    )


def market_timestamp(market, indices):
    if not indices.empty and "generatedTime" in indices.columns:
        value = indices.iloc[0]["generatedTime"]
        return str(value)

    if "last_updated" in market.columns:
        dates = pd.to_datetime(
            market["last_updated"], errors="coerce"
        ).dropna()

        if not dates.empty:
            return dates.max().strftime("%Y-%m-%d %H:%M:%S")

    return "Not available"


def back_home():
    if st.button("⬅ HOME", key="back_home"):
        st.session_state.page = "Home"
        st.rerun()


def company_details(df, key):
    if df.empty:
        return

    options = df["symbol"].astype(str).tolist()

    selected = st.selectbox(
        "Select company",
        options,
        key=key
    )

    company = df[df["symbol"].astype(str) == selected].iloc[0]

    st.markdown("### " + str(company.get("name", selected)))

    a, b, c = st.columns(3)

    a.metric("LTP", fmt(company.get("ltp")))
    b.metric("Change", fmt(company.get("change")))
    c.metric(
        "Change %",
        f"{safe_num(company.get('percent_change')):.2f}%"
    )

    details = {
        "Symbol": company.get("symbol"),
        "Company": company.get("name"),
        "Sector": company.get("sectorName"),
        "LTP": company.get("ltp"),
        "Previous Close": company.get("previous_close"),
        "Change": company.get("change"),
        "Change (%)": company.get("percent_change"),
        "Day High": company.get("high"),
        "Day Low": company.get("low"),
        "Volume": company.get("volume"),
        "Turnover": company.get("turnover"),
        "Trades": company.get("trades"),
        "Market Capitalization": company.get("market_cap")
    }

    st.table(
        pd.DataFrame(
            details.items(),
            columns=["Information", "Value"]
        )
    )

# ============================================================
# HEADER - ORIGINAL DESIGN
# ============================================================

st.markdown("""
<div class="edge-header">
    <div class="edge-logo">📈 NEPSE EDGE</div>
    <div class="edge-subtitle">
        NEPAL STOCK MARKET INTELLIGENCE
    </div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# SIDEBAR NAVIGATION
# ============================================================

with st.sidebar:

    st.markdown("## 📈 NEPSE EDGE")
    st.caption("MAIN NAVIGATION")
    st.divider()

    if st.button("🏠 HOME", use_container_width=True):
        st.session_state.page = "Home"
        st.rerun()

    for label, page in pages:
        if st.button(
            label,
            key="menu_" + page,
            use_container_width=True
        ):
            st.session_state.page = page
            st.rerun()

    st.divider()
    st.caption("NEPSE market information platform")
    st.caption("Public data source may be delayed.")

# ============================================================
# DATA LOAD
# ============================================================

try:
    market, equity = prepare_market()
    indices = load_indices()
    summary = load_summary()
    top_data = load_top_stocks()
    data_ok = True
    data_error = ""

except Exception as error:
    market = pd.DataFrame()
    equity = pd.DataFrame()
    indices = pd.DataFrame()
    summary = pd.DataFrame()
    top_data = {}
    data_ok = False
    data_error = str(error)

# ============================================================
# HOME PAGE - ORIGINAL EIGHT SQUARE BOXES
# ============================================================

if st.session_state.page == "Home":

    st.markdown(
        '<div class="section-heading">EXPLORE NEPSE</div>',
        unsafe_allow_html=True
    )

    # Original two-column layout preserved
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

    # Market snapshot below original boxes
    st.divider()

    st.markdown("### MARKET SNAPSHOT")

    if data_ok:

        nepse = get_index(indices, "NEPSE Index")

        turnover = summary_value(summary, "Total Turnover")
        volume = summary_value(summary, "Total Traded Shares")
        transactions = summary_value(summary, "Total Transactions")

        if nepse is not None:

            a, b, c = st.columns(3)

            a.metric(
                "NEPSE INDEX",
                fmt(nepse.get("close")),
                f"{safe_num(nepse.get('perChange')):.2f}%"
            )

            b.metric(
                "TURNOVER",
                money(turnover) if turnover is not None else "N/A"
            )

            c.metric(
                "SHARES TRADED",
                compact(volume) if volume is not None else "N/A"
            )

            d, e, f = st.columns(3)

            d.metric(
                "TRANSACTIONS",
                compact(transactions) if transactions is not None else "N/A"
            )

            e.metric("LISTED EQUITIES", len(equity))

            f.metric("MARKET INDICES", len(indices))

        else:
            st.info("NEPSE index data is unavailable.")

    else:
        st.warning("Market data could not be loaded.")

# ============================================================
# MARKET DASHBOARD
# ============================================================

elif st.session_state.page == "Market Dashboard":

    back_home()

    st.title("📊 MARKET DASHBOARD")
    st.caption("Complete Nepal Stock Market Overview")

    if not data_ok:
        st.error("Market data unavailable.")
        st.code(data_error)
        st.stop()

    # Refresh control
    if st.button("🔄 REFRESH MARKET DATA", key="refresh_market"):
        st.cache_data.clear()
        st.rerun()

    # Main NEPSE index
    st.markdown("## NEPSE INDEX")

    nepse = get_index(indices, "NEPSE Index")

    if nepse is not None:

        a, b, c, d = st.columns(4)

        a.metric(
            "NEPSE",
            fmt(nepse.get("close")),
            f"{safe_num(nepse.get('perChange')):.2f}%"
        )

        b.metric("POINT CHANGE", fmt(nepse.get("change")))
        c.metric("DAY HIGH", fmt(nepse.get("high")))
        d.metric("DAY LOW", fmt(nepse.get("low")))

        e, f = st.columns(2)

        e.metric("52 WEEK HIGH", fmt(nepse.get("fiftyTwoWeekHigh")))
        f.metric("52 WEEK LOW", fmt(nepse.get("fiftyTwoWeekLow")))

    else:
        st.warning("NEPSE index is unavailable.")

    # All indices
    st.divider()
    st.markdown("## ALL MARKET INDICES")

    show_table(
        indices,
        [
            "index", "close", "change",
            "perChange", "high", "low",
            "fiftyTwoWeekHigh", "fiftyTwoWeekLow"
        ]
    )

    # Market summary
    st.divider()
    st.markdown("## MARKET SUMMARY")

    turnover = summary_value(summary, "Total Turnover")
    volume = summary_value(summary, "Total Traded Shares")
    transactions = summary_value(summary, "Total Transactions")
    scrips = summary_value(summary, "Total Scrips Traded")
    market_cap = summary_value(summary, "Total Market Capitalization")
    float_cap = summary_value(summary, "Total Float Market Capitalization")

    a, b, c = st.columns(3)

    a.metric("TOTAL TURNOVER", money(turnover) if turnover is not None else "N/A")
    b.metric("SHARES TRADED", compact(volume) if volume is not None else "N/A")
    c.metric("TRANSACTIONS", compact(transactions) if transactions is not None else "N/A")

    d, e, f = st.columns(3)

    d.metric("SCRIPS TRADED", compact(scrips) if scrips is not None else "N/A")
    e.metric("MARKET CAPITALIZATION", money(market_cap) if market_cap is not None else "N/A")
    f.metric("FLOAT MARKET CAP", money(float_cap) if float_cap is not None else "N/A")

    # Market breadth
    st.divider()
    st.markdown("## MARKET BREADTH")

    changes = pd.to_numeric(
        equity["percent_change"], errors="coerce"
    )

    advancing = int((changes > 0).sum())
    declining = int((changes < 0).sum())
    unchanged = int((changes == 0).sum())
    missing = int(changes.isna().sum())

    a, b, c, d = st.columns(4)

    a.metric("🟢 ADVANCING", advancing)
    b.metric("🔴 DECLINING", declining)
    c.metric("⚪ UNCHANGED", unchanged)
    d.metric("NO DATA", missing)

    breadth = pd.DataFrame({
        "Market Movement": ["Advancing", "Declining", "Unchanged"],
        "Companies": [advancing, declining, unchanged]
    }).set_index("Market Movement")

    st.bar_chart(breadth)

    if advancing > declining:
        st.success("Market breadth is positive.")
    elif declining > advancing:
        st.warning("Market breadth is negative.")
    else:
        st.info("Market breadth is balanced.")

    # Top gainers and losers
    st.divider()
    st.markdown("## TOP GAINERS & LOSERS")

    equity_symbols = set(equity["symbol"].astype(str))

    gainers = pd.DataFrame(top_data.get("top_gainer", []))
    losers = pd.DataFrame(top_data.get("top_loser", []))

    if not gainers.empty and "symbol" in gainers.columns:
        gainers = gainers[
            gainers["symbol"].astype(str).isin(equity_symbols)
        ]

    if not losers.empty and "symbol" in losers.columns:
        losers = losers[
            losers["symbol"].astype(str).isin(equity_symbols)
        ]

    left, right = st.columns(2)

    with left:
        st.markdown("### 🟢 TOP GAINERS")
        show_table(
            gainers.head(10),
            ["symbol", "securityName", "ltp", "pointChange", "percentageChange"]
        )

    with right:
        st.markdown("### 🔴 TOP LOSERS")
        show_table(
            losers.head(10),
            ["symbol", "securityName", "ltp", "pointChange", "percentageChange"]
        )

    # Turnover leaders
    st.divider()
    st.markdown("## TOP TURNOVER")

    turnover_df = pd.DataFrame(top_data.get("top_turnover", []))

    if not turnover_df.empty:
        turnover_df = turnover_df[
            turnover_df["symbol"].astype(str).isin(equity_symbols)
        ]

    show_table(
        turnover_df.head(15),
        ["symbol", "securityName", "closingPrice", "turnover"]
    )

    # Volume leaders
    st.divider()
    st.markdown("## TOP VOLUME")

    volume_df = equity.sort_values(
        "volume", ascending=False
    ).head(15)

    show_table(
        volume_df,
        ["symbol", "name", "ltp", "percent_change", "volume", "turnover"]
    )

    # Sector performance
    st.divider()
    st.markdown("## SECTOR PERFORMANCE")

    sector_data = equity.copy()

    sector_data["percent_change"] = pd.to_numeric(
        sector_data["percent_change"], errors="coerce"
    )

    sector_data["turnover"] = pd.to_numeric(
        sector_data["turnover"], errors="coerce"
    )

    sector_summary = (
        sector_data.groupby("sectorName")
        .agg(
            Companies=("symbol", "count"),
            Average_Change=("percent_change", "mean"),
            Total_Turnover=("turnover", "sum")
        )
        .reset_index()
        .rename(columns={
            "sectorName": "Sector",
            "Average_Change": "Average Change (%)",
            "Total_Turnover": "Total Turnover"
        })
        .sort_values("Average Change (%)", ascending=False)
    )

    show_table(
        sector_summary,
        ["Sector", "Companies", "Average Change (%)", "Total Turnover"]
    )

    if not sector_summary.empty:
        chart = sector_summary.set_index("Sector")[
            ["Average Change (%)"]
        ]
        st.bar_chart(chart)

    # Full market table
    st.divider()
    st.markdown("## COMPLETE MARKET STOCK LIST")

    search = st.text_input(
        "Search company name or symbol",
        placeholder="Example: NABIL, NHPC, PHCL"
    )

    stock_table = equity.copy()

    if search:
        stock_table = stock_table[
            stock_table["symbol"].astype(str).str.contains(
                search, case=False, na=False
            )
            |
            stock_table["name"].astype(str).str.contains(
                search, case=False, na=False
            )
        ]

    st.caption(f"{len(stock_table)} companies found")

    show_table(
        stock_table,
        [
            "symbol", "name", "sectorName", "ltp",
            "change", "percent_change", "high",
            "low", "volume", "turnover", "trades"
        ],
        height=500
    )

    st.caption("Data timestamp: " + market_timestamp(market, indices))
    st.caption("Source: YONEPSE public data mirror. Not official NEPSE live data.")

# ============================================================
# STOCK SCANNER
# ============================================================

elif st.session_state.page == "Stock Scanner":

    back_home()
    st.title("🔍 STOCK SCANNER")
    st.caption("Search and filter listed equity companies")

    if not data_ok:
        st.error("Market data unavailable.")
        st.stop()

    df = equity.copy()

    search = st.text_input("Search by company name or symbol")

    sectors = sorted(df["sectorName"].dropna().astype(str).unique())

    a, b = st.columns(2)

    with a:
        sector = st.selectbox("Select Sector", ["All Sectors"] + sectors)

    with b:
        movement = st.selectbox(
            "Price Movement",
            ["All", "Gainers", "Losers", "Unchanged"]
        )

    if sector != "All Sectors":
        df = df[df["sectorName"] == sector]

    if search:
        df = df[
            df["symbol"].astype(str).str.contains(
                search, case=False, na=False
            )
            |
            df["name"].astype(str).str.contains(
                search, case=False, na=False
            )
        ]

    if movement == "Gainers":
        df = df[df["percent_change"] > 0]
    elif movement == "Losers":
        df = df[df["percent_change"] < 0]
    elif movement == "Unchanged":
        df = df[df["percent_change"] == 0]

    st.subheader(f"RESULTS: {len(df)} COMPANIES")

    show_table(
        df,
        [
            "symbol", "name", "sectorName",
            "ltp", "change", "percent_change",
            "volume", "turnover"
        ],
        height=500
    )

    st.divider()
    st.markdown("## COMPANY QUICK VIEW")
    company_details(df, "scanner_company")

# ============================================================
# SECTOR EXPLORER
# ============================================================

elif st.session_state.page == "Sector Explorer":

    back_home()
    st.title("🏢 SECTOR EXPLORER")

    if not data_ok:
        st.error("Market data unavailable.")
        st.stop()

    df = equity.copy()

    sectors = sorted(df["sectorName"].dropna().astype(str).unique())

    sector = st.selectbox(
        "SELECT SECTOR",
        ["All Sectors"] + sectors
    )

    search = st.text_input("Search company inside sector")

    if sector != "All Sectors":
        df = df[df["sectorName"] == sector]

    if search:
        df = df[
            df["symbol"].astype(str).str.contains(
                search, case=False, na=False
            )
            |
            df["name"].astype(str).str.contains(
                search, case=False, na=False
            )
        ]

    st.markdown(f"### {sector} | {len(df)} COMPANIES")

    a, b, c = st.columns(3)

    a.metric("COMPANIES", len(df))

    b.metric(
        "AVERAGE CHANGE",
        f"{safe_num(df['percent_change'].mean()):.2f}%"
        if not df.empty else "N/A"
    )

    c.metric(
        "TOTAL TURNOVER",
        money(df["turnover"].sum())
        if not df.empty else "N/A"
    )

    show_table(
        df,
        [
            "symbol", "name", "ltp",
            "percent_change", "volume", "turnover"
        ],
        height=450
    )

    st.divider()
    st.markdown("## SELECT COMPANY")
    company_details(df, "sector_company")

# ============================================================
# FUNDAMENTAL ANALYSIS
# ============================================================

elif st.session_state.page == "Fundamental Analysis":

    back_home()
    st.title("📚 FUNDAMENTAL ANALYSIS")

    st.markdown("### COMPANY FINANCIAL HEALTH")

    if data_ok:
        company_details(equity, "fundamental_company")

    st.divider()

    st.markdown("""
    **Financial analysis sections**

    - Earnings Per Share (EPS)
    - Price to Earnings Ratio (P/E)
    - Book Value Per Share
    - Net Worth
    - Quarterly Profit and Loss
    - Annual Financial Statements
    - Debt and Interest Analysis
    - Dividend History
    - Profit Growth
    - Company Valuation
    """)

    st.info(
        "Financial statement data integration is pending. "
        "Only verified financial figures will be displayed."
    )

# ============================================================
# TECHNICAL ANALYSIS
# ============================================================

elif st.session_state.page == "Technical Analysis":

    back_home()
    st.title("📈 TECHNICAL ANALYSIS")

    if data_ok:
        company_details(equity, "technical_company")

    st.divider()

    st.markdown("""
    **Technical analysis sections**

    - Candlestick Chart
    - RSI (14)
    - MACD
    - EMA 20 / 50 / 200
    - Bollinger Bands
    - ADX and Stochastic
    - Volume Analysis
    - Support and Resistance
    - Trend Analysis
    - Breakout Detection
    """)

    st.info(
        "Historical OHLC data integration is required "
        "before calculating technical indicators."
    )

# ============================================================
# NEWS INTELLIGENCE
# ============================================================

elif st.session_state.page == "News Intelligence":

    back_home()
    st.title("📰 NEWS INTELLIGENCE")

    st.markdown("""
    **News monitoring categories**

    - Company Announcements
    - Quarterly Financial Reports
    - Dividend and Bonus Shares
    - Right Share Announcements
    - AGM and Book Closure
    - Project Updates
    - NEPSE Notices
    - SEBON Notices
    - Positive / Negative / Neutral News Impact
    """)

    st.info(
        "Verified news source integration will be added "
        "before publishing company news or impact ratings."
    )

# ============================================================
# SMART RECOMMENDATIONS
# ============================================================

elif st.session_state.page == "Smart Recommendations":

    back_home()
    st.title("🧠 SMART RECOMMENDATIONS")

    st.markdown("### NEPSE OPPORTUNITY DISCOVERY")

    st.write(
        "Select a sector to explore companies for further analysis."
    )

    if data_ok:

        sectors = sorted(
            equity["sectorName"].dropna().astype(str).unique()
        )

        selected_sector = st.selectbox(
            "SELECT SECTOR",
            ["All Sectors"] + sectors,
            key="recommend_sector"
        )

        candidates = equity.copy()

        if selected_sector != "All Sectors":
            candidates = candidates[
                candidates["sectorName"] == selected_sector
            ]

        candidates = candidates.sort_values(
            "percent_change", ascending=False
        )

        show_table(
            candidates.head(20),
            [
                "symbol", "name", "sectorName",
                "ltp", "percent_change", "volume", "turnover"
            ]
        )

    st.divider()

    st.markdown("""
    **Recommendation engine will combine:**

    1. Fundamental strength
    2. Technical indicators
    3. Price action and volume
    4. Sector performance
    5. Overall NEPSE trend
    6. Company news and reports
    7. Breakout and false-breakout risk
    8. Risk and reward assessment
    """)

    st.warning(
        "This is currently a market discovery list, not a verified "
        "buy/sell recommendation engine. Scoring will be activated "
        "after reliable historical and fundamental data is connected."
    )

# ============================================================
# WATCHLIST & PORTFOLIO
# ============================================================

elif st.session_state.page == "Watchlist & Portfolio":

    back_home()
    st.title("💼 WATCHLIST & PORTFOLIO")

    st.markdown("### PERSONAL STOCK TRACKER")

    if data_ok:

        options = equity["symbol"].astype(str).tolist()

        selected = st.selectbox(
            "Select a company",
            options,
            key="portfolio_company"
        )

        company = equity[
            equity["symbol"].astype(str) == selected
        ].iloc[0]

        ltp = safe_num(company.get("ltp"))

        quantity = st.number_input(
            "Quantity",
            min_value=1,
            value=100,
            step=1
        )

        buy_price = st.number_input(
            "Average Purchase Price",
            min_value=0.0,
            value=float(ltp),
            step=1.0
        )

        investment = quantity * buy_price
        current_value = quantity * ltp
        profit_loss = current_value - investment

        a, b, c = st.columns(3)

        a.metric("INVESTMENT", money(investment))
        b.metric("CURRENT VALUE", money(current_value))
        c.metric("PROFIT / LOSS", money(profit_loss))

        st.caption(
            "This is a temporary calculator. "
            "Persistent portfolio saving will be added later."
        )

    st.divider()

    st.info(
        "Future features: saved watchlists, multiple holdings, "
        "average cost, realized profit, unrealized profit and "
        "portfolio diversification."
    )

# ============================================================
# FOOTER - ORIGINAL STYLE
# ============================================================

st.markdown("""
<div class="edge-footer">
    NEPSE EDGE © 2026<br>
    INDEPENDENT STOCK MARKET INTELLIGENCE PLATFORM
</div>
""", unsafe_allow_html=True)
