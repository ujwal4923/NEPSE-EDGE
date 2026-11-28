
import streamlit as st
import pandas as pd
import urllib.request
import json
from datetime import datetime

# =========================================================
# NEPSE EDGE | VERSION 2
# Complete Market Dashboard
# =========================================================

st.set_page_config(
    page_title="NEPSE EDGE",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

BASE = "https://raw.githubusercontent.com/Shubhamnpk/yonepse/main/data"

# =========================================================
# DESIGN
# =========================================================

st.markdown("""
<style>
.stApp {
    background: #0b1220;
    color: #e5e7eb;
}
.block-container {
    padding-top: 1.3rem;
    padding-bottom: 2rem;
    max-width: 1450px;
}
.main-title {
    font-size: 34px;
    font-weight: 900;
    letter-spacing: 1px;
    color: #38bdf8;
    margin-bottom: 0;
}
.sub-title {
    color: #94a3b8;
    font-size: 13px;
}
h1,h2,h3 {
    color: #f8fafc !important;
}
div[data-testid="stMetric"] {
    background: #172337;
    border: 1px solid #30445f;
    padding: 13px;
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
    font-size: 15px;
    font-weight: 800;
}
div.stButton > button:hover {
    border-color: #38bdf8;
    background: #203650;
    color: #38bdf8;
}
.info-card {
    background: #172337;
    border: 1px solid #30445f;
    border-radius: 12px;
    padding: 15px;
}
.small-note {
    color: #94a3b8;
    font-size: 12px;
}
hr {
    border-color: #263750;
}
@media(max-width:640px) {
    .main-title {font-size:27px;}
    .block-container {
        padding-left: .7rem;
        padding-right: .7rem;
    }
    div.stButton > button {
        min-height: 95px;
        font-size: 12px;
    }
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# DATA FUNCTIONS
# =========================================================

def fetch_json(path):
    url = BASE + "/" + path
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "NEPSE-EDGE"}
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


@st.cache_data(ttl=300)
def get_stocks():
    data = fetch_json("nepse_data.json")
    df = pd.DataFrame(data)

    numeric = [
        "ltp", "previous_close", "change",
        "percent_change", "high", "low",
        "volume", "turnover", "trades", "market_cap"
    ]

    for col in numeric:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


@st.cache_data(ttl=300)
def get_indices():
    return pd.DataFrame(fetch_json("market/indices.json"))


@st.cache_data(ttl=300)
def get_summary():
    return pd.DataFrame(fetch_json("market/summary.json"))


@st.cache_data(ttl=300)
def get_top_stocks():
    return fetch_json("market/top_stocks.json")


@st.cache_data(ttl=300)
def get_securities():
    return pd.DataFrame(fetch_json("other/securities.json"))


def load_all():
    stocks = get_stocks()
    indices = get_indices()
    summary = get_summary()
    top = get_top_stocks()
    securities = get_securities()

    if "symbol" in securities.columns:
        keep = ["symbol"]
        for col in ["sectorName", "instrumentType", "status",
                    "companyName", "securityName"]:
            if col in securities.columns:
                keep.append(col)

        securities = securities[keep].drop_duplicates("symbol")
        stocks = stocks.merge(securities, on="symbol", how="left")

    if "sectorName" not in stocks.columns:
        stocks["sectorName"] = "Unclassified"

    stocks["sectorName"] = stocks["sectorName"].fillna("Unclassified")

    return stocks, indices, summary, top


def num(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def fmt_num(value):
    return f"{num(value):,.2f}"


def compact(value):
    value = num(value)
    if abs(value) >= 1_000_000_000:
        return f"{value/1_000_000_000:.2f} B"
    if abs(value) >= 1_000_000:
        return f"{value/1_000_000:.2f} M"
    if abs(value) >= 1_000:
        return f"{value/1_000:,.2f} K"
    return f"{value:,.2f}"


def rupees(value):
    return "Rs. " + compact(value)


def summary_value(summary, keyword):
    if summary.empty or "detail" not in summary.columns:
        return 0

    found = summary[
        summary["detail"].astype(str).str.contains(
            keyword, case=False, na=False
        )
    ]

    if found.empty:
        return 0

    return num(found.iloc[0].get("value", 0))


def get_nepse_index(indices):
    if indices.empty or "index" not in indices.columns:
        return None

    result = indices[
        indices["index"].astype(str).str.contains(
            "NEPSE Index", case=False, na=False
        )
    ]

    return None if result.empty else result.iloc[0]


def display_table(df, columns, height=None):
    available = [c for c in columns if c in df.columns]
    if not available:
        st.info("No data available.")
        return

    st.dataframe(
        df[available],
        use_container_width=True,
        hide_index=True,
        height=height
    )


def market_timestamp(stocks, indices):
    if not indices.empty and "generatedTime" in indices.columns:
        try:
            return str(indices.iloc[0]["generatedTime"])
        except Exception:
            pass

    if "last_updated" in stocks.columns:
        dates = pd.to_datetime(
            stocks["last_updated"], errors="coerce"
        ).dropna()
        if not dates.empty:
            return dates.max().strftime("%Y-%m-%d %H:%M:%S")

    return "Timestamp unavailable"


# =========================================================
# NAVIGATION
# =========================================================

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


def home_button():
    if st.button("← BACK TO HOME"):
        st.session_state.page = "Home"
        st.rerun()


# =========================================================
# HEADER
# =========================================================

st.markdown(
    '<div class="main-title">📈 NEPSE EDGE</div>',
    unsafe_allow_html=True
)
st.markdown(
    '<div class="sub-title">NEPAL STOCK MARKET DISCOVERY & ANALYSIS PLATFORM</div>',
    unsafe_allow_html=True
)
st.markdown("---")

# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:
    st.markdown("## 📈 NEPSE EDGE")
    st.caption("Navigation Menu")

    selected = st.radio(
        "MAIN MENU",
        PAGES,
        index=PAGES.index(st.session_state.page)
    )

    if selected != st.session_state.page:
        st.session_state.page = selected
        st.rerun()

    st.markdown("---")
    st.caption("Public market data mirror")
    st.caption("Data may be delayed or incomplete.")

# =========================================================
# DATA LOADING
# =========================================================

if st.button("🔄 REFRESH MARKET DATA"):
    st.cache_data.clear()
    st.rerun()

try:
    stocks, indices, summary, top_data = load_all()
    data_ok = True
    error_message = ""
except Exception as error:
    stocks = pd.DataFrame()
    indices = pd.DataFrame()
    summary = pd.DataFrame()
    top_data = {}
    data_ok = False
    error_message = str(error)

# Active equity list for company/sector analysis
if data_ok:
    equity_stocks = stocks.copy()

    if "instrumentType" in equity_stocks.columns:
        equity_stocks = equity_stocks[
            equity_stocks["instrumentType"].astype(str).str.lower()
            == "equity"
        ]

    if "status" in equity_stocks.columns:
        active = equity_stocks[
            equity_stocks["status"].astype(str).str.upper() == "A"
        ]
        if not active.empty:
            equity_stocks = active

    equity_stocks = equity_stocks.drop_duplicates("symbol")


# =========================================================
# HOME PAGE
# =========================================================

if st.session_state.page == "Home":

    st.title("Welcome to NEPSE EDGE")

    st.write(
        "Explore Nepal's stock market through market data, "
        "sector analysis, company research and trading tools."
    )

    st.markdown("### EXPLORE MODULES")

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
        c1, c2 = st.columns(2)

        for col, item in zip(
            [c1, c2],
            menu_items[row * 2:row * 2 + 2]
        ):
            icon, title = item
            with col:
                if st.button(
                    icon + "\n\n" + title.upper(),
                    key="home_" + title
                ):
                    st.session_state.page = title
                    st.rerun()

    st.markdown("---")
    st.markdown("### MARKET SNAPSHOT")

    if data_ok:
        nepse = get_nepse_index(indices)

        if nepse is not None:
            a, b, c = st.columns(3)

            a.metric(
                "NEPSE INDEX",
                fmt_num(nepse.get("close")),
                f"{num(nepse.get('perChange')):.2f}%"
            )

            b.metric(
                "TURNOVER",
                rupees(summary_value(summary, "Total Turnover"))
            )

            c.metric(
                "SHARES TRADED",
                compact(summary_value(summary, "Total Traded Shares"))
            )
    else:
        st.warning("Market data is currently unavailable.")

# =========================================================
# MARKET DASHBOARD
# =========================================================

elif st.session_state.page == "Market Dashboard":

    home_button()
    st.title("📊 Market Dashboard")
    st.caption("Complete NEPSE market overview")

    if not data_ok:
        st.error("Market data could not be loaded.")
        st.code(error_message)
        st.stop()

    nepse = get_nepse_index(indices)

    # Main index
    st.markdown("## NEPSE INDEX")

    if nepse is not None:
        a, b, c, d = st.columns(4)

        a.metric(
            "NEPSE",
            fmt_num(nepse.get("close")),
            f"{num(nepse.get('perChange')):.2f}%"
        )
        b.metric("POINT CHANGE", fmt_num(nepse.get("change")))
        c.metric("DAY HIGH", fmt_num(nepse.get("high")))
        d.metric("DAY LOW", fmt_num(nepse.get("low")))

        high_52 = num(nepse.get("fiftyTwoWeekHigh"))
        low_52 = num(nepse.get("fiftyTwoWeekLow"))

        e, f = st.columns(2)
        e.metric("52 WEEK HIGH", fmt_num(high_52))
        f.metric("52 WEEK LOW", fmt_num(low_52))
    else:
        st.warning("NEPSE index information is unavailable.")

    # All indices
    st.markdown("---")
    st.markdown("## ALL MARKET INDICES")

    index_cols = [
        "index", "close", "change", "perChange",
        "high", "low", "fiftyTwoWeekHigh", "fiftyTwoWeekLow"
    ]

    display_table(indices, index_cols)

    # Market summary
    st.markdown("---")
    st.markdown("## MARKET SUMMARY")

    turnover = summary_value(summary, "Total Turnover")
    volume = summary_value(summary, "Total Traded Shares")
    transactions = summary_value(summary, "Total Transactions")
    scrips = summary_value(summary, "Total Scrips Traded")
    market_cap = summary_value(summary, "Total Market Capitalization")
    float_cap = summary_value(summary, "Total Float Market Capitalization")

    a, b, c = st.columns(3)
    a.metric("TOTAL TURNOVER", rupees(turnover))
    b.metric("SHARES TRADED", compact(volume))
    c.metric("TOTAL TRANSACTIONS", compact(transactions))

    d, e, f = st.columns(3)
    d.metric("SCRIPS TRADED", compact(scrips))
    e.metric("MARKET CAPITALIZATION", rupees(market_cap))
    f.metric("FLOAT MARKET CAP", rupees(float_cap))

    # Market breadth
    st.markdown("---")
    st.markdown("## MARKET BREADTH")

    breadth_df = equity_stocks.copy()
    breadth_df["percent_change"] = pd.to_numeric(
        breadth_df["percent_change"], errors="coerce"
    )

    advancing = int((breadth_df["percent_change"] > 0).sum())
    declining = int((breadth_df["percent_change"] < 0).sum())
    unchanged = int((breadth_df["percent_change"] == 0).sum())
    no_change_data = int(breadth_df["percent_change"].isna().sum())

    a, b, c, d = st.columns(4)
    a.metric("🟢 ADVANCING", advancing)
    b.metric("🔴 DECLINING", declining)
    c.metric("⚪ UNCHANGED", unchanged)
    d.metric("NO DATA", no_change_data)

    breadth_chart = pd.DataFrame({
        "Market Movement": ["Advancing", "Declining", "Unchanged"],
        "Companies": [advancing, declining, unchanged]
    }).set_index("Market Movement")

    st.bar_chart(breadth_chart)

    if advancing > declining:
        st.success("More companies advanced than declined.")
    elif declining > advancing:
        st.warning("More companies declined than advanced.")
    else:
        st.info("Advancing and declining companies are balanced.")

    # Top gainers and losers
    st.markdown("---")
    st.markdown("## TOP GAINERS & LOSERS")

    gainers = pd.DataFrame(top_data.get("top_gainer", []))
    losers = pd.DataFrame(top_data.get("top_loser", []))

    left, right = st.columns(2)

    with left:
        st.markdown("### 🟢 Top Gainers")
        display_table(
            gainers,
            ["symbol", "securityName", "ltp", "pointChange", "percentageChange"]
        )

    with right:
        st.markdown("### 🔴 Top Losers")
        display_table(
            losers,
            ["symbol", "securityName", "ltp", "pointChange", "percentageChange"]
        )

    # Turnover leaders
    st.markdown("---")
    st.markdown("## TOP TURNOVER")

    turnover_df = pd.DataFrame(top_data.get("top_turnover", []))

    display_table(
        turnover_df,
        ["symbol", "securityName", "closingPrice", "turnover"]
    )

    # Volume leaders
    st.markdown("---")
    st.markdown("## TOP VOLUME")

    volume_df = equity_stocks.sort_values(
        "volume", ascending=False
    ).head(15)

    display_table(
        volume_df,
        ["symbol", "name", "ltp", "percent_change", "volume", "turnover"]
    )

    # Sector performance
    st.markdown("---")
    st.markdown("## SECTOR PERFORMANCE")

    sector_data = equity_stocks.copy()

    sector_data["percent_change"] = pd.to_numeric(
        sector_data["percent_change"], errors="coerce"
    )
    sector_data["turnover"] = pd.to_numeric(
        sector_data["turnover"], errors="coerce"
    )

    sector_summary = (
        sector_data.groupby("sectorName", dropna=False)
        .agg(
            Companies=("symbol", "count"),
            Average_Change=("percent_change", "mean"),
            Total_Turnover=("turnover", "sum")
        )
        .reset_index()
    )

    sector_summary = sector_summary.rename(
        columns={
            "sectorName": "Sector",
            "Average_Change": "Average Change (%)",
            "Total_Turnover": "Total Turnover"
        }
    )

    sector_summary = sector_summary.sort_values(
        "Average Change (%)", ascending=False
    )

    display_table(
        sector_summary,
        ["Sector", "Companies", "Average Change (%)", "Total Turnover"]
    )

    if not sector_summary.empty:
        chart_sector = sector_summary.set_index("Sector")[
            ["Average Change (%)"]
        ]
        st.bar_chart(chart_sector)

    # Market data details
    st.markdown("---")
    st.markdown("## MARKET DATA TABLE")

    search = st.text_input(
        "Search company or symbol",
        placeholder="Enter symbol or company name",
        key="dashboard_search"
    )

    table_df = equity_stocks.copy()

    if search:
        table_df = table_df[
            table_df["symbol"].astype(str).str.contains(
                search, case=False, na=False
            )
            |
            table_df["name"].astype(str).str.contains(
                search, case=False, na=False
            )
        ]

    st.caption(f"{len(table_df)} companies found")

    display_table(
        table_df,
        [
            "symbol", "name", "sectorName", "ltp",
            "change", "percent_change", "high", "low",
            "volume", "turnover", "trades"
        ],
        height=450
    )

    st.markdown("---")
    st.caption("Data timestamp: " + market_timestamp(stocks, indices))
    st.caption("Source: YONEPSE public data mirror. Not official NEPSE live data.")

# =========================================================
# STOCK SCANNER
# =========================================================

elif st.session_state.page == "Stock Scanner":

    home_button()
    st.title("🔎 Stock Scanner")

    if not data_ok:
        st.error("Market data unavailable.")
        st.stop()

    df = equity_stocks.copy()

    search = st.text_input("Search company name or symbol")

    sectors = sorted(df["sectorName"].dropna().astype(str).unique())

    a, b = st.columns(2)

    with a:
        sector = st.selectbox("Sector", ["All Sectors"] + sectors)

    with b:
        movement = st.selectbox(
            "Market Movement",
            ["All", "Gainers", "Losers", "Unchanged"]
        )

    if search:
        df = df[
            df["symbol"].astype(str).str.contains(search, case=False, na=False)
            |
            df["name"].astype(str).str.contains(search, case=False, na=False)
        ]

    if sector != "All Sectors":
        df = df[df["sectorName"] == sector]

    if movement == "Gainers":
        df = df[df["percent_change"] > 0]
    elif movement == "Losers":
        df = df[df["percent_change"] < 0]
    elif movement == "Unchanged":
        df = df[df["percent_change"] == 0]

    st.subheader(f"Results: {len(df)} companies")

    display_table(
        df,
        ["symbol", "name", "sectorName", "ltp",
         "change", "percent_change", "volume", "turnover"],
        height=500
    )

    if not df.empty:
        symbol = st.selectbox(
            "Select company for quick details",
            df["symbol"].astype(str).tolist()
        )

        company = df[df["symbol"] == symbol].iloc[0]

        st.markdown("### " + str(company["name"]))

        a, b, c = st.columns(3)
        a.metric("LTP", fmt_num(company.get("ltp")))
        b.metric("Change", fmt_num(company.get("change")))
        c.metric("Change %", f"{num(company.get('percent_change')):.2f}%")


# =========================================================
# SECTOR EXPLORER
# =========================================================

elif st.session_state.page == "Sector Explorer":

    home_button()
    st.title("🏢 Sector Explorer")

    if not data_ok:
        st.error("Market data unavailable.")
        st.stop()

    df = equity_stocks.copy()
    sectors = sorted(df["sectorName"].dropna().astype(str).unique())

    sector = st.selectbox("Choose Sector", ["All Sectors"] + sectors)
    search = st.text_input("Search company in selected sector")

    if sector != "All Sectors":
        df = df[df["sectorName"] == sector]

    if search:
        df = df[
            df["symbol"].astype(str).str.contains(search, case=False, na=False)
            |
            df["name"].astype(str).str.contains(search, case=False, na=False)
        ]

    st.subheader(f"{sector} | {len(df)} companies")

    display_table(
        df,
        ["symbol", "name", "ltp", "percent_change", "volume", "turnover"],
        height=450
    )

    if not df.empty:
        a, b, c = st.columns(3)
        a.metric("Companies", len(df))
        b.metric(
            "Average Change",
            f"{num(df['percent_change'].mean()):.2f}%"
        )
        c.metric(
            "Total Turnover",
            rupees(df["turnover"].sum())
        )

        symbol = st.selectbox(
            "Select company for details",
            df["symbol"].astype(str).tolist(),
            key="sector_symbol"
        )

        company = df[df["symbol"] == symbol].iloc[0]

        st.markdown("### " + str(company["name"]))

        details = {
            "Symbol": company.get("symbol"),
            "Company": company.get("name"),
            "Sector": company.get("sectorName"),
            "LTP": company.get("ltp"),
            "Previous Close": company.get("previous_close"),
            "Change": company.get("change"),
            "Change (%)": company.get("percent_change"),
            "High": company.get("high"),
            "Low": company.get("low"),
            "Volume": company.get("volume"),
            "Turnover": company.get("turnover"),
            "Trades": company.get("trades"),
            "Market Cap": company.get("market_cap")
        }

        st.table(
            pd.DataFrame(
                details.items(),
                columns=["Information", "Value"]
            )
        )


# =========================================================
# OTHER MODULES
# =========================================================

elif st.session_state.page == "Fundamental Analysis":

    home_button()
    st.title("📘 Fundamental Analysis")
    st.info(
        "EPS, P/E, Book Value, Net Worth, Profit Growth, "
        "Debt Analysis and Quarterly Reports will be added here."
    )
    st.warning(
        "Verified financial statements are not connected yet. "
        "No financial values are invented."
    )

elif st.session_state.page == "Technical Analysis":

    home_button()
    st.title("📈 Technical Analysis")
    st.info(
        "Candlestick charts, RSI, MACD, EMA 20/50/200, "
        "Bollinger Bands, Volume, Support and Resistance."
    )
    st.warning(
        "Reliable historical OHLC data is required before "
        "technical indicators can be calculated."
    )

elif st.session_state.page == "News Intelligence":

    home_button()
    st.title("📰 News Intelligence")
    st.info(
        "Company news, NEPSE notices, dividends, bonus shares, "
        "right shares, AGM, book closure and project updates."
    )
    st.warning("News sources are not connected yet.")

elif st.session_state.page == "Smart Recommendations":

    home_button()
    st.title("🤖 Smart Recommendations")

    st.markdown("### NEPSE Opportunity Discovery")

    st.write(
        "The recommendation engine will scan the full listed market "
        "and combine the following information:"
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
        "Verified data will be connected before showing signals."
    )

elif st.session_state.page == "Watchlist & Portfolio":

    home_button()
    st.title("⭐ Watchlist & Portfolio")

    st.info(
        "Users will be able to create watchlists, enter purchase "
        "prices and quantities, and track portfolio performance."
    )

    st.caption(
        "The main scanner will cover all NEPSE-listed companies, "
        "not only personal holdings."
    )


# =========================================================
# FOOTER
# =========================================================

st.markdown("---")

st.markdown(
    '<div style="text-align:center;color:#64748b;font-size:12px;">'
    'NEPSE EDGE © 2026 | Nepal Stock Market Analysis Platform'
    '</div>',
    unsafe_allow_html=True
)
