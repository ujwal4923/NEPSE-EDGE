
import streamlit as st
import pandas as pd
import urllib.request
import json
from datetime import datetime

# ==========================================================
# NEPSE EDGE - COMPLETE APP VERSION 1
# Market Dashboard + Stock Scanner + Sector Explorer
# ==========================================================

st.set_page_config(
    page_title="NEPSE EDGE",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

APP_TITLE = "NEPSE EDGE"
BASE_URL = "https://raw.githubusercontent.com/Shubhamnpk/yonepse/main/data"

# ==========================================================
# DESIGN / CSS
# ==========================================================

st.markdown("""
<style>
    .stApp {
        background-color: #0b1220;
        color: #e5e7eb;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }

    h1, h2, h3 {
        color: #f8fafc !important;
    }

    .main-title {
        font-size: 34px;
        font-weight: 900;
        letter-spacing: 1px;
        color: #38bdf8;
        margin-bottom: 0px;
    }

    .sub-title {
        color: #94a3b8;
        font-size: 14px;
        margin-top: 2px;
    }

    .section-heading {
        font-size: 21px;
        font-weight: 800;
        color: #f1f5f9;
        margin-top: 20px;
        margin-bottom: 12px;
    }

    div[data-testid="stMetric"] {
        background: #172337;
        border: 1px solid #263750;
        padding: 15px;
        border-radius: 12px;
    }

    div[data-testid="stMetricLabel"] {
        color: #94a3b8;
    }

    div[data-testid="stMetricValue"] {
        color: #f8fafc;
    }

    div.stButton > button {
        width: 100%;
        min-height: 105px;
        border-radius: 14px;
        border: 1px solid #30445f;
        background: #172337;
        color: #f8fafc;
        font-size: 16px;
        font-weight: 800;
        transition: 0.2s;
    }

    div.stButton > button:hover {
        border: 1px solid #38bdf8;
        background: #203650;
        color: #38bdf8;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #263750;
        border-radius: 10px;
    }

    .info-box {
        background: #172337;
        border: 1px solid #30445f;
        padding: 15px;
        border-radius: 12px;
        margin-bottom: 12px;
    }

    .small-note {
        color: #94a3b8;
        font-size: 12px;
    }

    hr {
        border-color: #263750;
    }

    @media (max-width: 640px) {
        .main-title {
            font-size: 27px;
        }

        .block-container {
            padding-left: 0.8rem;
            padding-right: 0.8rem;
        }

        div.stButton > button {
            min-height: 100px;
            font-size: 13px;
            padding: 8px;
        }
    }
</style>
""", unsafe_allow_html=True)


# ==========================================================
# DATA FUNCTIONS
# ==========================================================

@st.cache_data(ttl=300)
def fetch_json(path):
    url = BASE_URL + "/" + path

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "NEPSE-EDGE"}
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def number(value, default=0):
    try:
        result = float(value)
        if pd.isna(result):
            return default
        return result
    except (ValueError, TypeError):
        return default


def money(value):
    return "Rs. {:,.2f}".format(number(value))


def compact_number(value):
    value = number(value)

    if value >= 1000000000:
        return "{:.2f} B".format(value / 1000000000)

    if value >= 1000000:
        return "{:.2f} M".format(value / 1000000)

    if value >= 1000:
        return "{:,.0f}".format(value)

    return "{:.2f}".format(value)


@st.cache_data(ttl=300)
def load_market_data():

    raw = fetch_json("nepse_data.json")

    if not isinstance(raw, list) or len(raw) == 0:
        raise ValueError("Market data is empty.")

    df = pd.DataFrame(raw)

    required = ["symbol", "name", "ltp", "percent_change", "volume"]

    for col in required:
        if col not in df.columns:
            df[col] = None

    numeric_columns = [
        "ltp", "change", "percent_change",
        "volume", "turnover", "high", "low",
        "previous_close", "trades", "market_cap"
    ]

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Add company sector information
    try:
        securities = fetch_json("other/securities.json")
        sec = pd.DataFrame(securities)

        if "symbol" in sec.columns:
            columns = ["symbol"]

            for col in ["sectorName", "instrumentType", "status"]:
                if col in sec.columns:
                    columns.append(col)

            sec = sec[columns].drop_duplicates("symbol")

            df = df.merge(
                sec,
                on="symbol",
                how="left"
            )

    except Exception:
        df["sectorName"] = "Unclassified"

    if "sectorName" not in df.columns:
        df["sectorName"] = "Unclassified"

    df["sectorName"] = df["sectorName"].fillna("Unclassified")

    if "instrumentType" in df.columns:
        equity = df[
            df["instrumentType"].astype(str).str.lower() == "equity"
        ]

        if not equity.empty:
            df = equity.copy()

    df = df.drop_duplicates("symbol")
    df = df[df["symbol"].notna()].copy()

    return df


@st.cache_data(ttl=300)
def load_indices():
    return pd.DataFrame(fetch_json("market/indices.json"))


@st.cache_data(ttl=300)
def load_summary():
    return pd.DataFrame(fetch_json("market/summary.json"))


def summary_value(summary_df, keyword):

    if summary_df.empty:
        return 0

    if "detail" not in summary_df.columns:
        return 0

    result = summary_df[
        summary_df["detail"].astype(str).str.contains(
            keyword,
            case=False,
            na=False
        )
    ]

    if result.empty:
        return 0

    return number(result.iloc[0].get("value", 0))


def market_timestamp(df):

    if "last_updated" not in df.columns:
        return "Timestamp unavailable"

    dates = pd.to_datetime(df["last_updated"], errors="coerce").dropna()

    if dates.empty:
        return "Timestamp unavailable"

    latest = dates.max()

    return latest.strftime("%Y-%m-%d %H:%M:%S")


# ==========================================================
# NAVIGATION
# ==========================================================

PAGES = [
    "Home",
    "Market Dashboard",
    "Stock Scanner",
    "Sector Explorer",
    "Fundamental Analysis",
    "Technical Analysis",
    "News Intelligence",
    "Smart Recommendations",
    "Watchlist & Portfolio"
]

if "page" not in st.session_state:
    st.session_state.page = "Home"


def go_to_page(page):
    st.session_state.page = page


def home_button():
    if st.button("← HOME", key="home_return"):
        st.session_state.page = "Home"
        st.rerun()


# ==========================================================
# HEADER
# ==========================================================

st.markdown(
    '<div class="main-title">📈 NEPSE EDGE</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="sub-title">NEPAL STOCK MARKET DISCOVERY & ANALYSIS PLATFORM</div>',
    unsafe_allow_html=True
)

st.markdown("---")


# ==========================================================
# SIDEBAR MENU
# ==========================================================

with st.sidebar:

    st.markdown("## 📈 NEPSE EDGE")
    st.caption("Navigation Menu")

    selected_page = st.radio(
        "MAIN MENU",
        PAGES,
        index=PAGES.index(st.session_state.page),
        key="sidebar_navigation"
    )

    if selected_page != st.session_state.page:
        st.session_state.page = selected_page
        st.rerun()

    st.markdown("---")
    st.caption("Data source: YONEPSE public data mirror")
    st.caption("Data may be delayed or incomplete.")


# ==========================================================
# LOAD MARKET DATA
# ==========================================================

@st.cache_data(ttl=300)
def get_all_market_data():

    market = load_market_data()

    try:
        indices = load_indices()
    except Exception:
        indices = pd.DataFrame()

    try:
        summary = load_summary()
    except Exception:
        summary = pd.DataFrame()

    return market, indices, summary


try:
    market_df, indices_df, summary_df = get_all_market_data()
    data_loaded = True
    data_error = ""

except Exception as e:
    market_df = pd.DataFrame()
    indices_df = pd.DataFrame()
    summary_df = pd.DataFrame()
    data_loaded = False
    data_error = str(e)


# ==========================================================
# HOME PAGE
# ==========================================================

if st.session_state.page == "Home":

    st.markdown("## Welcome to NEPSE EDGE")

    st.markdown(
        "Explore Nepal's stock market through market data, "
        "sector analysis, company research and trading tools."
    )

    st.markdown("### Explore Modules")

    menu_items = [
        ("📊", "Market Dashboard"),
        ("🔎", "Stock Scanner"),
        ("🏢", "Sector Explorer"),
        ("📘", "Fundamental Analysis"),
        ("📈", "Technical Analysis"),
        ("📰", "News Intelligence"),
        ("🤖", "Smart Recommendations"),
        ("⭐", "Watchlist & Portfolio")
    ]

    for row in range(4):

        col1, col2 = st.columns(2)

        for col, item in zip(
            [col1, col2],
            menu_items[row * 2: row * 2 + 2]
        ):

            icon, title = item

            with col:
                if st.button(
                    icon + "\n\n" + title.upper(),
                    key="menu_" + title,
                    use_container_width=True
                ):
                    st.session_state.page = title
                    st.rerun()

    st.markdown("---")

    if data_loaded:

        st.markdown("### Market Snapshot")

        nepse = None

        if not indices_df.empty and "index" in indices_df.columns:
            found = indices_df[
                indices_df["index"].astype(str).str.contains(
                    "NEPSE Index",
                    case=False,
                    na=False
                )
            ]

            if not found.empty:
                nepse = found.iloc[0]

        if nepse is not None:

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "NEPSE INDEX",
                "{:,.2f}".format(number(nepse.get("close"))),
                "{:.2f}%".format(number(nepse.get("perChange")))
            )

            c2.metric(
                "TURNOVER",
                "Rs. " + compact_number(
                    summary_value(summary_df, "Total Turnover")
                )
            )

            c3.metric(
                "TRADED SHARES",
                compact_number(
                    summary_value(summary_df, "Total Traded Shares")
                )
            )

    else:
        st.warning("Market data is currently unavailable.")

    st.markdown("---")
    st.markdown(
        '<div class="small-note">NEPSE EDGE © 2026</div>',
        unsafe_allow_html=True
    )


# ==========================================================
# MARKET DASHBOARD
# ==========================================================

elif st.session_state.page == "Market Dashboard":

    home_button()

    st.title("📊 Market Dashboard")
    st.caption("NEPSE market overview and trading activity")

    if not data_loaded:
        st.error("Unable to load market data.")
        st.code(data_error)
        st.stop()

    # Main index
    nepse = None

    if not indices_df.empty and "index" in indices_df.columns:

        found = indices_df[
            indices_df["index"].astype(str).str.contains(
                "NEPSE Index",
                case=False,
                na=False
            )
        ]

        if not found.empty:
            nepse = found.iloc[0]

    if nepse is not None:

        st.markdown("### NEPSE Index")

        a, b, c, d = st.columns(4)

        a.metric(
            "NEPSE",
            "{:,.2f}".format(number(nepse.get("close"))),
            "{:.2f}%".format(number(nepse.get("perChange")))
        )

        b.metric(
            "Point Change",
            "{:,.2f}".format(number(nepse.get("change")))
        )

        c.metric(
            "Day High",
            "{:,.2f}".format(number(nepse.get("high")))
        )

        d.metric(
            "Day Low",
            "{:,.2f}".format(number(nepse.get("low")))
        )

    # Other indices
    st.markdown("### Other Market Indices")

    if not indices_df.empty:

        display_indices = indices_df.copy()

        index_columns = [
            "index", "close", "change", "perChange",
            "high", "low"
        ]

        available = [
            col for col in index_columns
            if col in display_indices.columns
        ]

        st.dataframe(
            display_indices[available],
            use_container_width=True,
            hide_index=True
        )

    # Market summary
    st.markdown("### Market Summary")

    total_turnover = summary_value(
        summary_df, "Total Turnover"
    )

    total_volume = summary_value(
        summary_df, "Total Traded Shares"
    )

    total_transactions = summary_value(
        summary_df, "Total Transactions"
    )

    total_scrips = summary_value(
        summary_df, "Total Scrips Traded"
    )

    market_cap = summary_value(
        summary_df, "Total Market Capitalization"
    )

    c1, c2, c3 = st.columns(3)

    c1.metric("Turnover", "Rs. " + compact_number(total_turnover))
    c2.metric("Shares Traded", compact_number(total_volume))
    c3.metric("Transactions", compact_number(total_transactions))

    c4, c5, c6 = st.columns(3)

    c4.metric("Scrips Traded", compact_number(total_scrips))
    c5.metric("Market Cap", "Rs. " + compact_number(market_cap))
    c6.metric("Companies / Securities", str(len(market_df)))

    # Market breadth
    st.markdown("### Market Breadth")

    positive = int((market_df["percent_change"] > 0).sum())
    negative = int((market_df["percent_change"] < 0).sum())
    unchanged = int((market_df["percent_change"] == 0).sum())

    x, y, z = st.columns(3)

    x.metric("Advancing", positive)
    y.metric("Declining", negative)
    z.metric("Unchanged", unchanged)

    breadth_df = pd.DataFrame({
        "Market Movement": ["Advancing", "Declining", "Unchanged"],
        "Companies": [positive, negative, unchanged]
    })

    st.bar_chart(
        breadth_df.set_index("Market Movement")
    )

    # Gainers and losers
    st.markdown("### Top Gainers & Losers")

    gainers = market_df.sort_values(
        "percent_change",
        ascending=False
    ).head(10)

    losers = market_df.sort_values(
        "percent_change",
        ascending=True
    ).head(10)

    left, right = st.columns(2)

    with left:
        st.markdown("#### 🟢 Top Gainers")

        cols = [
            "symbol", "ltp", "percent_change", "volume"
        ]

        st.dataframe(
            gainers[[c for c in cols if c in gainers.columns]],
            use_container_width=True,
            hide_index=True
        )

    with right:
        st.markdown("#### 🔴 Top Losers")

        st.dataframe(
            losers[[c for c in cols if c in losers.columns]],
            use_container_width=True,
            hide_index=True
        )

    # Most traded
    st.markdown("### Most Traded Companies")

    if "turnover" in market_df.columns:

        most_traded = market_df.sort_values(
            "turnover",
            ascending=False
        ).head(10)

        st.dataframe(
            most_traded[
                ["symbol", "name", "ltp", "turnover", "volume"]
            ],
            use_container_width=True,
            hide_index=True
        )

    # Sector performance
    st.markdown("### Sector Performance")

    sector_df = market_df.copy()

    sector_df["percent_change"] = pd.to_numeric(
        sector_df["percent_change"],
        errors="coerce"
    )

    sector_performance = (
        sector_df.groupby("sectorName")["percent_change"]
        .mean()
        .dropna()
        .sort_values(ascending=False)
    )

    if not sector_performance.empty:

        sector_table = sector_performance.reset_index()
        sector_table.columns = [
            "Sector", "Average Change (%)"
        ]

        st.dataframe(
            sector_table,
            use_container_width=True,
            hide_index=True
        )

        st.bar_chart(
            sector_performance
        )

    st.caption(
        "Last available stock data timestamp: "
        + market_timestamp(market_df)
    )


# ==========================================================
# STOCK SCANNER
# ==========================================================

elif st.session_state.page == "Stock Scanner":

    home_button()

    st.title("🔎 Stock Scanner")
    st.caption("Search and filter NEPSE-listed companies")

    if not data_loaded:
        st.error("Market data unavailable.")
        st.stop()

    search = st.text_input(
        "Search by company name or symbol",
        placeholder="Example: NABIL, NHPC, Hydropower..."
    )

    col1, col2 = st.columns(2)

    sectors = sorted(
        market_df["sectorName"].dropna().astype(str).unique()
    )

    with col1:
        sector_filter = st.selectbox(
            "Select Sector",
            ["All Sectors"] + sectors
        )

    with col2:
        movement_filter = st.selectbox(
            "Market Movement",
            ["All", "Gainers", "Losers", "Unchanged"]
        )

    filtered = market_df.copy()

    if search:
        filtered = filtered[
            filtered["symbol"].astype(str).str.contains(
                search, case=False, na=False
            )
            |
            filtered["name"].astype(str).str.contains(
                search, case=False, na=False
            )
        ]

    if sector_filter != "All Sectors":
        filtered = filtered[
            filtered["sectorName"] == sector_filter
        ]

    if movement_filter == "Gainers":
        filtered = filtered[filtered["percent_change"] > 0]

    elif movement_filter == "Losers":
        filtered = filtered[filtered["percent_change"] < 0]

    elif movement_filter == "Unchanged":
        filtered = filtered[filtered["percent_change"] == 0]

    st.markdown(
        "### Results: " + str(len(filtered)) + " companies"
    )

    display_columns = [
        "symbol", "name", "sectorName", "ltp",
        "change", "percent_change", "volume", "turnover"
    ]

    available_columns = [
        c for c in display_columns
        if c in filtered.columns
    ]

    st.dataframe(
        filtered[available_columns].sort_values(
            "percent_change",
            ascending=False
        ),
        use_container_width=True,
        hide_index=True
    )

    if not filtered.empty:

        st.markdown("### View Company")

        selected_symbol = st.selectbox(
            "Select a company",
            filtered["symbol"].astype(str).tolist()
        )

        selected_company = filtered[
            filtered["symbol"] == selected_symbol
        ].iloc[0]

        st.markdown("#### " + str(selected_company["name"]))

        a, b, c = st.columns(3)

        a.metric(
            "LTP",
            money(selected_company.get("ltp"))
        )

        b.metric(
            "Change",
            "{:.2f}".format(number(selected_company.get("change")))
        )

        c.metric(
            "Change %",
            "{:.2f}%".format(
                number(selected_company.get("percent_change"))
            )
        )

        st.write("Sector:", selected_company.get("sectorName"))
        st.write("Symbol:", selected_company.get("symbol"))


# ==========================================================
# SECTOR EXPLORER
# ==========================================================

elif st.session_state.page == "Sector Explorer":

    home_button()

    st.title("🏢 Sector Explorer")
    st.caption("Explore companies sector by sector")

    if not data_loaded:
        st.error("Market data unavailable.")
        st.stop()

    sectors = sorted(
        market_df["sectorName"].dropna().astype(str).unique()
    )

    selected_sector = st.selectbox(
        "Choose a Sector",
        ["All Sectors"] + sectors
    )

    search = st.text_input(
        "Search company inside selected sector",
        placeholder="Enter company name or symbol"
    )

    sector_companies = market_df.copy()

    if selected_sector != "All Sectors":

        sector_companies = sector_companies[
            sector_companies["sectorName"] == selected_sector
        ]

    if search:

        sector_companies = sector_companies[
            sector_companies["symbol"].astype(str).str.contains(
                search, case=False, na=False
            )
            |
            sector_companies["name"].astype(str).str.contains(
                search, case=False, na=False
            )
        ]

    st.markdown(
        "### " + selected_sector
        + " — " + str(len(sector_companies)) + " companies"
    )

    if not sector_companies.empty:

        columns = [
            "symbol", "name", "ltp",
            "percent_change", "volume", "turnover"
        ]

        available = [
            c for c in columns
            if c in sector_companies.columns
        ]

        st.dataframe(
            sector_companies[available].sort_values(
                "percent_change",
                ascending=False
            ),
            use_container_width=True,
            hide_index=True
        )

        st.markdown("### Sector Market Overview")

        average_change = sector_companies[
            "percent_change"
        ].mean()

        total_volume = sector_companies[
            "volume"
        ].sum()

        total_turnover = sector_companies[
            "turnover"
        ].sum()

        a, b, c = st.columns(3)

        a.metric(
            "Average Change",
            "{:.2f}%".format(number(average_change))
        )

        b.metric(
            "Total Volume",
            compact_number(total_volume)
        )

        c.metric(
            "Total Turnover",
            "Rs. " + compact_number(total_turnover)
        )

        st.markdown("### Select Company for Details")

        company_symbol = st.selectbox(
            "Company",
            sector_companies["symbol"].astype(str).tolist(),
            key="sector_company"
        )

        company = sector_companies[
            sector_companies["symbol"] == company_symbol
        ].iloc[0]

        st.markdown("#### " + str(company["name"]))

        details = {
            "Symbol": company.get("symbol"),
            "Company": company.get("name"),
            "Sector": company.get("sectorName"),
            "Last Traded Price": company.get("ltp"),
            "Change": company.get("change"),
            "Change (%)": company.get("percent_change"),
            "Day High": company.get("high"),
            "Day Low": company.get("low"),
            "Volume": company.get("volume"),
            "Turnover": company.get("turnover"),
            "Market Capitalization": company.get("market_cap")
        }

        st.table(
            pd.DataFrame(
                details.items(),
                columns=["Information", "Value"]
            )
        )

    else:
        st.info("No companies found for this selection.")


# ==========================================================
# FUNDAMENTAL ANALYSIS
# ==========================================================

elif st.session_state.page == "Fundamental Analysis":

    home_button()

    st.title("📘 Fundamental Analysis")

    st.info(
        "This module will provide company financial analysis, "
        "including EPS, P/E Ratio, Book Value, Net Worth, "
        "Profit Growth, Debt and quarterly reports."
    )

    st.warning(
        "Verified company financial statement data has not "
        "yet been connected. No financial values are invented."
    )


# ==========================================================
# TECHNICAL ANALYSIS
# ==========================================================

elif st.session_state.page == "Technical Analysis":

    home_button()

    st.title("📈 Technical Analysis")

    st.info(
        "This module will include candlestick charts, "
        "RSI, MACD, EMA 20/50/200, Bollinger Bands, "
        "volume analysis, support and resistance."
    )

    st.warning(
        "Reliable historical OHLC data is required before "
        "technical indicators can be calculated correctly."
    )


# ==========================================================
# NEWS INTELLIGENCE
# ==========================================================

elif st.session_state.page == "News Intelligence":

    home_button()

    st.title("📰 News Intelligence")

    st.info(
        "This module will collect company news, NEPSE notices, "
        "dividend announcements, bonus shares, right shares, "
        "AGM notices, book closure and project updates."
    )

    st.warning(
        "News sources have not yet been connected."
    )


# ==========================================================
# SMART RECOMMENDATIONS
# ==========================================================

elif st.session_state.page == "Smart Recommendations":

    home_button()

    st.title("🤖 Smart Recommendations")

    st.markdown(
        "### NEPSE Opportunity Discovery"
    )

    st.info(
        "This will be the main intelligence module of NEPSE EDGE."
    )

    st.write(
        "The system will scan all listed companies and combine:"
    )

    st.markdown("""
    - Fundamental strength
    - Technical indicators
    - Price action and volume
    - Sector performance
    - Overall NEPSE market trend
    - Company news and reports
    - Breakout and false-breakout risk
    - Risk and reward assessment
    """)

    st.warning(
        "Recommendation scoring is not activated yet. "
        "We will build it using verified data rather than "
        "showing unsupported buy or sell signals."
    )


# ==========================================================
# WATCHLIST & PORTFOLIO
# ==========================================================

elif st.session_state.page == "Watchlist & Portfolio":

    home_button()

    st.title("⭐ Watchlist & Portfolio")

    st.info(
        "This optional module will allow users to create "
        "their own watchlist, add purchase prices and quantities, "
        "and monitor portfolio performance."
    )

    st.caption(
        "The main NEPSE EDGE scanner will always cover "
        "the entire listed market, not only personal holdings."
    )


# ==========================================================
# FOOTER
# ==========================================================

st.markdown("---")

st.markdown(
    '<div style="text-align:center;color:#64748b;font-size:12px;">'
    'NEPSE EDGE © 2026 | Nepal Stock Market Analysis Platform'
    '</div>',
    unsafe_allow_html=True
)
