
import streamlit as st
import pandas as pd
import urllib.request
import json
import sqlite3
import os
from datetime import date, datetime
from collections import deque

# =========================================================
# NEPSE EDGE - PERSONAL MARKET & PORTFOLIO APPLICATION
# =========================================================

st.set_page_config(
    page_title="NEPSE EDGE",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

APP_TITLE = "NEPSE EDGE"
BASE = "https://raw.githubusercontent.com/Shubhamnpk/yonepse/main/data"
DB_PATH = "nepse_edge_portfolio.db"

# ---------------------------------------------------------
# SECURITY
# Optional password protection through Streamlit Secrets:
# APP_PASSWORD = "your-private-password"
# ---------------------------------------------------------

def check_password():
    password = st.secrets.get("APP_PASSWORD", "")
    if not password:
        st.warning(
            "Portfolio security is not configured. "
            "Set APP_PASSWORD in Streamlit Secrets before "
            "using this application with personal records."
        )
        return True

    if st.session_state.get("authenticated"):
        return True

    st.title("🔐 NEPSE EDGE Login")
    entered = st.text_input("Enter application password", type="password")

    if st.button("Login", type="primary"):
        if entered == password:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False


# ---------------------------------------------------------
# DATA FUNCTIONS
# ---------------------------------------------------------

@st.cache_data(ttl=300)
def get_data(path):
    url = BASE + "/" + path
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "NEPSE-EDGE"}
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def safe_number(value, default=0.0):
    try:
        result = float(value)
        if pd.isna(result):
            return default
        return result
    except (ValueError, TypeError):
        return default


def money(value):
    return "Rs. {:,.2f}".format(safe_number(value))


def load_market():
    data = get_data("nepse_data.json")

    if not isinstance(data, list) or not data:
        raise ValueError("Market data is empty.")

    df = pd.DataFrame(data)

    # Security classification
    try:
        securities = get_data("other/securities.json")
        sec = pd.DataFrame(securities)

        if "symbol" in sec.columns:
            keep = ["symbol"]
            for col in ["instrumentType", "sectorName", "status"]:
                if col in sec.columns:
                    keep.append(col)

            sec = sec[keep].drop_duplicates("symbol")
            df = df.merge(sec, on="symbol", how="left")
    except Exception:
        pass

    # Exclude open-ended funds where identifiable
    if "asset_type" in df.columns:
        df = df[
            df["asset_type"].astype(str).str.lower()
            != "open_ended_mutual_fund"
        ]

    # Prefer equity records if classification is available
    if "instrumentType" in df.columns:
        equity = df[
            df["instrumentType"].astype(str).str.lower() == "equity"
        ]
        if not equity.empty:
            df = equity.copy()

    if "symbol" not in df.columns:
        raise ValueError("Symbol field is missing.")

    if "name" not in df.columns:
        df["name"] = df["symbol"]

    for col in [
        "ltp", "change", "percent_change",
        "volume", "turnover", "high", "low"
    ]:
        if col not in df.columns:
            df[col] = None
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["symbol"] = df["symbol"].astype(str).str.upper()
    df = df.drop_duplicates("symbol")

    return df


def load_sectors():
    try:
        data = get_data("other/sector_codes.json")
        mapping = {}

        if isinstance(data, dict):
            for sector, members in data.items():
                if isinstance(members, list):
                    for item in members:
                        if isinstance(item, dict) and item.get("symbol"):
                            mapping[str(item["symbol"]).upper()] = sector

        return mapping
    except Exception:
        return {}


# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------

def db_connect():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    with db_connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL DEFAULT 0,
                fees REAL DEFAULT 0,
                notes TEXT DEFAULT ''
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        conn.commit()


def get_transactions():
    with db_connect() as conn:
        return pd.read_sql_query(
            "SELECT * FROM transactions ORDER BY trade_date, id",
            conn
        )


def add_transaction(
    trade_date, symbol, action,
    quantity, price, fees, notes
):
    with db_connect() as conn:
        conn.execute("""
            INSERT INTO transactions
            (trade_date, symbol, action, quantity, price, fees, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(trade_date),
            symbol.upper().strip(),
            action,
            float(quantity),
            float(price),
            float(fees),
            notes
        ))
        conn.commit()


def delete_transaction(transaction_id):
    with db_connect() as conn:
        conn.execute(
            "DELETE FROM transactions WHERE id = ?",
            (int(transaction_id),)
        )
        conn.commit()


def get_setting(key, default):
    with db_connect() as conn:
        result = conn.execute(
            "SELECT value FROM settings WHERE key = ?",
            (key,)
        ).fetchone()

    return result[0] if result else str(default)


def save_setting(key, value):
    with db_connect() as conn:
        conn.execute("""
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """, (key, str(value)))
        conn.commit()


init_db()


# ---------------------------------------------------------
# TAX CALCULATION
# Resident natural person - listed shares
# Rates are configurable in Settings.
# ---------------------------------------------------------

def tax_rate_for_date(sale_date, holding_days):
    sale_date = pd.to_datetime(sale_date).date()

    if sale_date >= date(2026, 9, 22):
        return (
            3.75 if holding_days > 365 else 5.0
        ) / 100

    if sale_date >= date(2026, 7, 17):
        return (
            7.5 if holding_days > 365 else 10.0
        ) / 100

    return (
        5.0 if holding_days > 365 else 7.5
    ) / 100


# ---------------------------------------------------------
# FIFO PORTFOLIO CALCULATION
# BUY = normal purchase
# SELL = sale
# BONUS = bonus shares (zero-cost lot)
# RIGHT = right shares (price is subscription cost)
# DIVIDEND = cash dividend
# ADJUSTMENT = manual share quantity adjustment
# ---------------------------------------------------------

def calculate_portfolio(transactions, market_df):

    lots = {}
    realized = {}
    dividends = {}
    tax_total = {}
    fees_total = {}
    warnings = []

    if transactions.empty:
        return {}, {}, {}, {}, [], warnings

    tx = transactions.sort_values(
        ["trade_date", "id"]
    )

    for _, row in tx.iterrows():

        symbol = str(row["symbol"]).upper()
        action = str(row["action"]).upper()
        qty = safe_number(row["quantity"])
        price = safe_number(row["price"])
        fees = safe_number(row["fees"])
        trade_date = pd.to_datetime(row["trade_date"]).date()

        lots.setdefault(symbol, [])
        realized.setdefault(symbol, 0.0)
        dividends.setdefault(symbol, 0.0)
        tax_total.setdefault(symbol, 0.0)
        fees_total.setdefault(symbol, 0.0)

        fees_total[symbol] += fees

        if action in ["BUY", "RIGHT"]:
            total_cost = qty * price + fees

            lots[symbol].append({
                "quantity": qty,
                "cost_per_share": total_cost / qty if qty else 0,
                "date": trade_date
            })

        elif action == "BONUS":
            lots[symbol].append({
                "quantity": qty,
                "cost_per_share": 0.0,
                "date": trade_date
            })

        elif action == "ADJUSTMENT":
            if qty > 0:
                lots[symbol].append({
                    "quantity": qty,
                    "cost_per_share": price,
                    "date": trade_date
                })
            elif qty < 0:
                warnings.append(
                    f"{symbol}: negative adjustment requires review."
                )

        elif action == "DIVIDEND":
            dividends[symbol] += qty * price

        elif action == "SELL":

            remaining = qty
            gross_proceeds = qty * price
            net_proceeds = gross_proceeds - fees
            total_cost = 0.0
            weighted_holding_days = 0.0

            for lot in lots[symbol]:
                if remaining <= 0:
                    break

                available = lot["quantity"]
                used = min(remaining, available)

                total_cost += used * lot["cost_per_share"]

                holding_days = (
                    trade_date - lot["date"]
                ).days

                weighted_holding_days += used * holding_days

                lot["quantity"] -= used
                remaining -= used

            lots[symbol] = [
                lot for lot in lots[symbol]
                if lot["quantity"] > 0.000001
            ]

            if remaining > 0:
                warnings.append(
                    f"{symbol}: sold quantity exceeds recorded holdings "
                    f"by {remaining:g} shares. Please check transactions."
                )

            sold_qty = qty - remaining

            if sold_qty > 0:
                allocated_proceeds = (
                    net_proceeds * sold_qty / qty if qty else 0
                )

                gain = allocated_proceeds - total_cost
                realized[symbol] += gain

                average_days = int(
                    weighted_holding_days / sold_qty
                )

                rate = tax_rate_for_date(
                    trade_date, average_days
                )

                # Tax only on positive gain
                tax = max(gain, 0) * rate
                tax_total[symbol] += tax

    holdings = {}

    market_lookup = {}
    if not market_df.empty:
        for _, item in market_df.iterrows():
            market_lookup[str(item["symbol"]).upper()] = safe_number(
                item.get("ltp")
            )

    for symbol, symbol_lots in lots.items():

        quantity = sum(lot["quantity"] for lot in symbol_lots)
        cost = sum(
            lot["quantity"] * lot["cost_per_share"]
            for lot in symbol_lots
        )

        avg_cost = cost / quantity if quantity else 0
        ltp = market_lookup.get(symbol, 0)
        market_value = quantity * ltp

        holdings[symbol] = {
            "Symbol": symbol,
            "Quantity": quantity,
            "Average Cost": avg_cost,
            "Invested Cost": cost,
            "LTP": ltp,
            "Market Value": market_value,
            "Unrealized P/L": market_value - cost,
            "Realized P/L": realized.get(symbol, 0),
            "Dividend": dividends.get(symbol, 0),
            "Estimated CGT": tax_total.get(symbol, 0),
            "Fees": fees_total.get(symbol, 0)
        }

    return (
        holdings,
        realized,
        dividends,
        tax_total,
        fees_total,
        warnings
    )


# ---------------------------------------------------------
# PAGE DESIGN
# ---------------------------------------------------------

st.title("📈 NEPSE EDGE")
st.caption("Personal Market Intelligence & Portfolio Management")

if not check_password():
    st.stop()

st.sidebar.title("NEPSE EDGE")
st.sidebar.caption("Market Intelligence Platform")

pages = [
    "Home",
    "Market Dashboard",
    "Stock Scanner",
    "Sector Explorer",
    "Smart Recommendations",
    "Technical Analysis",
    "Fundamental Analysis",
    "News Intelligence",
    "My Portfolio",
    "Settings"
]

page = st.sidebar.radio(
    "MAIN MENU",
    pages,
    key="main_page"
)

# ---------------------------------------------------------
# MARKET DATA
# ---------------------------------------------------------

market_df = pd.DataFrame()
sector_map = {}
market_error = None

try:
    market_df = load_market()
    sector_map = load_sectors()
    market_df["Sector"] = (
        market_df["symbol"].map(sector_map).fillna("Unclassified")
    )
except Exception as error:
    market_error = str(error)

if market_error:
    st.warning(
        "Market data is temporarily unavailable. "
        "Portfolio records can still be accessed."
    )
    st.caption(market_error)

# ---------------------------------------------------------
# HOME
# ---------------------------------------------------------

if page == "Home":

    st.header("Welcome to NEPSE EDGE")

    st.write(
        "Your personal NEPSE market analysis, "
        "stock discovery and investment management system."
    )

    if not market_df.empty:

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Available Securities",
            len(market_df)
        )

        c2.metric(
            "Total Turnover",
            money(market_df["turnover"].fillna(0).sum())
        )

        c3.metric(
            "Total Volume",
            "{:,.0f}".format(
                market_df["volume"].fillna(0).sum()
            )
        )

        advances = int(
            (market_df["percent_change"] > 0).sum()
        )

        declines = int(
            (market_df["percent_change"] < 0).sum()
        )

        c4.metric(
            "Advances / Declines",
            f"{advances} / {declines}"
        )

    st.divider()
    st.subheader("Application Modules")

    descriptions = {
        "Market Dashboard": "NEPSE index, market breadth and turnover",
        "Stock Scanner": "Search and filter listed securities",
        "Sector Explorer": "Explore companies sector by sector",
        "Smart Recommendations": "Discover momentum and breakout candidates",
        "Technical Analysis": "Historical price and indicator analysis",
        "Fundamental Analysis": "Financial reports and valuation",
        "News Intelligence": "Company announcements and market news",
        "My Portfolio": "Your personal transactions and profit/loss"
    }

    modules = list(descriptions.keys())

    for start in range(0, len(modules), 2):
        col1, col2 = st.columns(2)

        for col, module in zip(
            [col1, col2], modules[start:start + 2]
        ):
            with col:
                st.markdown(f"### {module}")
                st.caption(descriptions[module])

                if st.button(
                    "Open " + module,
                    key="home_" + module,
                    use_container_width=True
                ):
                    st.session_state.main_page = module
                    st.rerun()

    st.info(
        "Select a module from the sidebar or open it above. "
        "Only the selected module will be displayed."
    )


# ---------------------------------------------------------
# MARKET DASHBOARD
# ---------------------------------------------------------

elif page == "Market Dashboard":

    st.header("📊 Market Dashboard")

    if market_df.empty:
        st.warning("Market data unavailable.")
    else:

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Total Securities",
            len(market_df)
        )

        c2.metric(
            "Turnover",
            money(market_df["turnover"].fillna(0).sum())
        )

        c3.metric(
            "Volume",
            "{:,.0f}".format(
                market_df["volume"].fillna(0).sum()
            )
        )

        advances = int(
            (market_df["percent_change"] > 0).sum()
        )

        declines = int(
            (market_df["percent_change"] < 0).sum()
        )

        unchanged = int(
            (market_df["percent_change"] == 0).sum()
        )

        st.subheader("Market Breadth")

        a, b, c = st.columns(3)
        a.metric("Advances", advances)
        b.metric("Declines", declines)
        c.metric("Unchanged", unchanged)

        breadth = pd.DataFrame({
            "Category": ["Advances", "Declines", "Unchanged"],
            "Securities": [advances, declines, unchanged]
        }).set_index("Category")

        st.bar_chart(breadth)

        st.subheader("NEPSE Indices")

        try:
            indices = pd.DataFrame(
                get_data("market/indices.json")
            )

            if not indices.empty:
                for _, item in indices.iterrows():

                    name = item.get("index", "Index")

                    value = safe_number(item.get("close"))
                    change = safe_number(item.get("change"))
                    pct = safe_number(item.get("perChange"))

                    st.metric(
                        name,
                        "{:,.2f}".format(value),
                        "{:,.2f} ({:.2f}%)".format(change, pct)
                    )
        except Exception:
            st.info("Index data unavailable.")

        st.subheader("Top Gainers and Losers")

        left, right = st.columns(2)

        with left:
            st.write("Top 10 Gainers")
            st.dataframe(
                market_df.nlargest(10, "percent_change")[
                    ["symbol", "name", "ltp", "percent_change"]
                ],
                use_container_width=True,
                hide_index=True
            )

        with right:
            st.write("Top 10 Losers")
            st.dataframe(
                market_df.nsmallest(10, "percent_change")[
                    ["symbol", "name", "ltp", "percent_change"]
                ],
                use_container_width=True,
                hide_index=True
            )

        st.subheader("Sector Performance")

        sector_summary = (
            market_df.groupby("Sector")
            .agg(
                Companies=("symbol", "count"),
                Average_Change=("percent_change", "mean"),
                Turnover=("turnover", "sum")
            )
            .reset_index()
            .sort_values("Average_Change", ascending=False)
        )

        st.dataframe(
            sector_summary,
            use_container_width=True,
            hide_index=True
        )

        st.caption(
            "Sector average is calculated from available constituent "
            "stocks. It is not an official weighted sector index."
        )


# ---------------------------------------------------------
# STOCK SCANNER
# ---------------------------------------------------------

elif page == "Stock Scanner":

    st.header("🔎 Stock Scanner")

    if market_df.empty:
        st.warning("Market data unavailable.")
    else:

        search = st.text_input(
            "Search Company or Symbol",
            placeholder="Example: NABIL, NGPL"
        )

        sectors = ["All Sectors"] + sorted(
            market_df["Sector"].dropna().unique().tolist()
        )

        selected_sector = st.selectbox(
            "Select Sector",
            sectors
        )

        sort_option = st.selectbox(
            "Sort By",
            [
                "Top Gainers",
                "Top Losers",
                "Highest Volume",
                "Highest Turnover"
            ]
        )

        result = market_df.copy()

        if selected_sector != "All Sectors":
            result = result[
                result["Sector"] == selected_sector
            ]

        if search.strip():
            mask = (
                result["symbol"].str.contains(
                    search, case=False, na=False
                )
                |
                result["name"].astype(str).str.contains(
                    search, case=False, na=False
                )
            )

            result = result[mask]

        sort_columns = {
            "Top Gainers": ("percent_change", False),
            "Top Losers": ("percent_change", True),
            "Highest Volume": ("volume", False),
            "Highest Turnover": ("turnover", False)
        }

        sort_col, ascending = sort_columns[sort_option]

        result = result.sort_values(
            sort_col,
            ascending=ascending,
            na_position="last"
        )

        st.write("Results:", len(result))

        display_cols = [
            "symbol", "name", "Sector",
            "ltp", "change", "percent_change",
            "volume", "turnover"
        ]

        display_cols = [
            col for col in display_cols
            if col in result.columns
        ]

        st.dataframe(
            result[display_cols],
            use_container_width=True,
            hide_index=True
        )


# ---------------------------------------------------------
# SECTOR EXPLORER
# ---------------------------------------------------------

elif page == "Sector Explorer":

    st.header("🏭 Sector Explorer")

    if market_df.empty:
        st.warning("Market data unavailable.")
    else:

        sector_list = ["All Sectors"] + sorted(
            market_df["Sector"].dropna().unique().tolist()
        )

        sector = st.selectbox(
            "Choose Sector",
            sector_list
        )

        company_search = st.text_input(
            "Search Company",
            key="sector_company_search"
        )

        result = market_df.copy()

        if sector != "All Sectors":
            result = result[result["Sector"] == sector]

        if company_search.strip():
            result = result[
                result["symbol"].str.contains(
                    company_search, case=False, na=False
                )
                |
                result["name"].astype(str).str.contains(
                    company_search, case=False, na=False
                )
            ]

        st.write("Companies found:", len(result))

        st.dataframe(
            result[
                [
                    c for c in [
                        "symbol", "name", "Sector",
                        "ltp", "percent_change",
                        "volume", "turnover"
                    ]
                    if c in result.columns
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

        if not result.empty:

            symbol = st.selectbox(
                "Select Company for Details",
                result["symbol"].tolist()
            )

            company = result[
                result["symbol"] == symbol
            ].iloc[0]

            st.subheader(
                str(company["name"]) + " (" + symbol + ")"
            )

            c1, c2, c3 = st.columns(3)

            c1.metric("LTP", money(company["ltp"]))
            c2.metric(
                "Change %",
                "{:.2f}%".format(
                    safe_number(company["percent_change"])
                )
            )
            c3.metric(
                "Volume",
                "{:,.0f}".format(
                    safe_number(company["volume"])
                )
            )

            if st.button("Add to Watchlist"):
                add_transaction(
                    date.today(),
                    symbol,
                    "WATCH",
                    0,
                    0,
                    0,
                    "Watchlist entry"
                )
                st.success("Watchlist record added.")


# ---------------------------------------------------------
# SMART RECOMMENDATIONS
# ---------------------------------------------------------

elif page == "Smart Recommendations":

    st.header("🧠 Smart Recommendations")

    st.write(
        "Market-wide stock discovery using available market data. "
        "These are screening candidates, not guaranteed buy signals."
    )

    if market_df.empty:
        st.warning("Market data unavailable.")
    else:

        sector = st.selectbox(
            "Select Sector",
            ["All Sectors"] + sorted(
                market_df["Sector"].dropna().unique().tolist()
            )
        )

        category = st.selectbox(
            "Select Opportunity Type",
            [
                "Daily Momentum Watchlist",
                "Strong Daily Gainers",
                "High Volume Activity",
                "Positive Market Performers"
            ]
        )

        candidates = market_df.copy()

        if sector != "All Sectors":
            candidates = candidates[
                candidates["Sector"] == sector
            ]

        if category == "Daily Momentum Watchlist":
            candidates = candidates[
                candidates["percent_change"] > 0
            ].sort_values(
                "percent_change", ascending=False
            )

        elif category == "Strong Daily Gainers":
            candidates = candidates[
                candidates["percent_change"] >= 2
            ].sort_values(
                "percent_change", ascending=False
            )

        elif category == "High Volume Activity":
            candidates = candidates.sort_values(
                "volume", ascending=False
            )

        else:
            candidates = candidates[
                candidates["percent_change"] > 0
            ].sort_values(
                "percent_change", ascending=False
            )

        st.subheader("Available Candidates")

        st.dataframe(
            candidates[
                [
                    c for c in [
                        "symbol", "name", "Sector",
                        "ltp", "percent_change",
                        "volume", "turnover"
                    ]
                    if c in candidates.columns
                ]
            ].head(30),
            use_container_width=True,
            hide_index=True
        )

        st.warning(
            "IMPORTANT: The current data feed does not establish "
            "complete historical OHLCV for every stock. RSI, MACD, "
            "EMA crossovers, ADX, Bollinger Bands, chart patterns "
            "and confirmed breakouts are therefore not claimed here. "
            "Historical data integration is required before these "
            "signals can be calculated reliably."
        )

        st.subheader("Breakout Analysis Status")

        st.info(
            "Breakout confirmation will require historical candles, "
            "resistance calculation, closing-price confirmation and "
            "volume comparison. This module will be expanded after "
            "a verified historical data source is connected."
        )


# ---------------------------------------------------------
# TECHNICAL ANALYSIS
# ---------------------------------------------------------

elif page == "Technical Analysis":

    st.header("📉 Technical Analysis")

    st.write(
        "Upload historical OHLCV data to calculate technical indicators."
    )

    if not market_df.empty:

        symbol = st.selectbox(
            "Select NEPSE Company",
            market_df["symbol"].tolist()
        )

        selected = market_df[
            market_df["symbol"] == symbol
        ].iloc[0]

        st.metric(
            "Current Market Price",
            money(selected["ltp"])
        )

    uploaded = st.file_uploader(
        "Upload Historical OHLCV CSV",
        type=["csv"]
    )

    st.caption(
        "CSV should contain Date, Open, High, Low, Close, Volume columns."
    )

    if uploaded is not None:

        try:
            hist = pd.read_csv(uploaded)

            hist.columns = [
                str(c).strip().lower()
                for c in hist.columns
            ]

            required = [
                "date", "open", "high",
                "low", "close", "volume"
            ]

            if not all(c in hist.columns for c in required):
                st.error(
                    "CSV must contain Date, Open, High, Low, "
                    "Close and Volume columns."
                )
            else:

                hist["date"] = pd.to_datetime(
                    hist["date"], errors="coerce"
                )

                for col in required[1:]:
                    hist[col] = pd.to_numeric(
                        hist[col], errors="coerce"
                    )

                hist = hist.dropna(
                    subset=["date", "close"]
                ).sort_values("date")

                close = hist["close"]

                hist["EMA20"] = close.ewm(
                    span=20, adjust=False
                ).mean()

                hist["EMA50"] = close.ewm(
                    span=50, adjust=False
                ).mean()

                hist["SMA200"] = close.rolling(200).mean()

                delta = close.diff()

                gain = delta.clip(lower=0)
                loss = -delta.clip(upper=0)

                avg_gain = gain.ewm(
                    alpha=1/14, adjust=False
                ).mean()

                avg_loss = loss.ewm(
                    alpha=1/14, adjust=False
                ).mean()

                rs = avg_gain / avg_loss.replace(0, float("nan"))

                hist["RSI14"] = 100 - (100 / (1 + rs))

                ema12 = close.ewm(
                    span=12, adjust=False
                ).mean()

                ema26 = close.ewm(
                    span=26, adjust=False
                ).mean()

                hist["MACD"] = ema12 - ema26

                hist["MACD_Signal"] = hist["MACD"].ewm(
                    span=9, adjust=False
                ).mean()

                hist["BB_Middle"] = close.rolling(20).mean()

                std = close.rolling(20).std()

                hist["BB_Upper"] = (
                    hist["BB_Middle"] + 2 * std
                )

                hist["BB_Lower"] = (
                    hist["BB_Middle"] - 2 * std
                )

                hist["Volume_Avg20"] = (
                    hist["volume"].rolling(20).mean()
                )

                st.subheader("Price Chart")

                st.line_chart(
                    hist.set_index("date")[
                        ["close", "EMA20", "EMA50", "SMA200"]
                    ]
                )

                st.subheader("RSI")

                st.line_chart(
                    hist.set_index("date")[["RSI14"]]
                )

                st.subheader("MACD")

                st.line_chart(
                    hist.set_index("date")[
                        ["MACD", "MACD_Signal"]
                    ]
                )

                st.subheader("Bollinger Bands")

                st.line_chart(
                    hist.set_index("date")[
                        ["close", "BB_Upper", "BB_Middle", "BB_Lower"]
                    ]
                )

                st.subheader("Latest Indicator Values")

                latest = hist.iloc[-1]

                c1, c2, c3 = st.columns(3)

                c1.metric(
                    "RSI (14)",
                    round(safe_number(latest["RSI14"]), 2)
                )

                c2.metric(
                    "MACD",
                    round(safe_number(latest["MACD"]), 2)
                )

                c3.metric(
                    "EMA 20",
                    round(safe_number(latest["EMA20"]), 2)
                )

                st.subheader("Latest Historical Data")

                st.dataframe(
                    hist.tail(20),
                    use_container_width=True,
                    hide_index=True
                )

                st.caption(
                    "Indicators are calculated from the uploaded CSV. "
                    "Verify the data source, date range and completeness."
                )

        except Exception as error:
            st.error("Unable to analyse this CSV.")
            st.caption(str(error))


# ---------------------------------------------------------
# FUNDAMENTAL ANALYSIS
# ---------------------------------------------------------

elif page == "Fundamental Analysis":

    st.header("📚 Fundamental Analysis")

    st.info(
        "This module will display EPS, P/E, Net Profit, Book Value, "
        "Debt, quarterly growth and financial reports when a verified "
        "financial-report source is connected."
    )

    if not market_df.empty:

        symbol = st.selectbox(
            "Select Company",
            market_df["symbol"].tolist(),
            key="fundamental_symbol"
        )

        company = market_df[
            market_df["symbol"] == symbol
        ].iloc[0]

        st.subheader(
            str(company["name"]) + " (" + symbol + ")"
        )

        c1, c2, c3 = st.columns(3)

        c1.metric("LTP", money(company["ltp"]))

        c2.metric(
            "Daily Change",
            "{:.2f}%".format(
                safe_number(company["percent_change"])
            )
        )

        c3.metric(
            "Turnover",
            money(company["turnover"])
        )

        st.warning(
            "Financial report endpoint and field structure have not "
            "yet been verified. Missing EPS, profit, debt or book-value "
            "figures will not be invented."
        )

        st.write(
            "Planned report sections: quarterly EPS, net profit, "
            "profit growth, P/E, book value, debt/equity, "
            "annual reports and dividend history."
        )


# ---------------------------------------------------------
# NEWS INTELLIGENCE
# ---------------------------------------------------------

elif page == "News Intelligence":

    st.header("📰 News Intelligence")

    st.info(
        "News integration will be activated after reliable sources "
        "for NEPSE announcements, company reports, SEBON notices "
        "and project updates are verified."
    )

    st.write("Planned analysis:")
    st.markdown("""
    - Company-specific news
    - Quarterly and annual report announcements
    - Dividend, bonus and right share notices
    - AGM and book closure
    - Hydropower project updates
    - SEBON and NEPSE notices
    - Positive, negative and neutral impact classification
    - Source and publication date
    """)


# ---------------------------------------------------------
# MY PORTFOLIO
# ---------------------------------------------------------

elif page == "My Portfolio":

    st.header("💼 My Portfolio")

    transactions = get_transactions()

    # Watchlist records are not financial transactions
    financial_transactions = transactions[
        transactions["action"].isin([
            "BUY", "SELL", "BONUS",
            "RIGHT", "DIVIDEND", "ADJUSTMENT"
        ])
    ].copy()

    (
        holdings,
        realized,
        dividends,
        tax_total,
        fees_total,
        warnings
    ) = calculate_portfolio(
        financial_transactions,
        market_df
    )

    holdings_df = pd.DataFrame(
        list(holdings.values())
    )

    if not holdings_df.empty:
        total_cost = holdings_df["Invested Cost"].sum()
        market_value = holdings_df["Market Value"].sum()
        unrealized = holdings_df["Unrealized P/L"].sum()
        realized_total = sum(realized.values())
        dividend_total = sum(dividends.values())
        estimated_tax = sum(tax_total.values())

    else:
        total_cost = 0
        market_value = 0
        unrealized = 0
        realized_total = 0
        dividend_total = 0
        estimated_tax = 0

    total_profit = (
        realized_total + unrealized + dividend_total - estimated_tax
    )

    total_return = (
        total_profit / total_cost * 100
        if total_cost else 0
    )

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Overview",
        "Add Transaction",
        "Holdings",
        "History",
        "Reports"
    ])

    # -----------------------------------------------------
    # PORTFOLIO OVERVIEW
    # -----------------------------------------------------

    with tab1:

        c1, c2 = st.columns(2)

        c1.metric(
            "Invested Cost",
            money(total_cost)
        )

        c2.metric(
            "Current Market Value",
            money(market_value)
        )

        c3, c4 = st.columns(2)

        c3.metric(
            "Unrealized P/L",
            money(unrealized)
        )

        c4.metric(
            "Realized P/L",
            money(realized_total)
        )

        c5, c6 = st.columns(2)

        c5.metric(
            "Dividend Income",
            money(dividend_total)
        )

        c6.metric(
            "Estimated Net Return",
            "{:.2f}%".format(total_return)
        )

        st.subheader("Portfolio Performance")

        st.metric(
            "Estimated Total Profit / Loss",
            money(total_profit)
        )

        if not holdings_df.empty:

            st.subheader("Holdings Distribution")

            st.bar_chart(
                holdings_df.set_index("Symbol")["Market Value"]
            )

            st.subheader("Company-wise Profit / Loss")

            st.bar_chart(
                holdings_df.set_index("Symbol")["Unrealized P/L"]
            )

        else:
            st.info(
                "No holdings recorded yet. Add your first "
                "purchase in Add Transaction."
            )

        for warning in warnings:
            st.warning(warning)

    # -----------------------------------------------------
    # ADD TRANSACTION
    # -----------------------------------------------------

    with tab2:

        st.subheader("Add Portfolio Record")

        action_options = [
            "BUY",
            "SELL",
            "BONUS",
            "RIGHT",
            "DIVIDEND",
            "ADJUSTMENT"
        ]

        with st.form("add_transaction_form"):

            action = st.selectbox(
                "Transaction Type",
                action_options
            )

            symbol_input = st.text_input(
                "Company Symbol",
                placeholder="Example: PHCL"
            )

            trade_date = st.date_input(
                "Transaction Date",
                value=date.today()
            )

            quantity = st.number_input(
                "Quantity / Shares",
                min_value=0.0,
                value=100.0,
                step=1.0
            )

            price = st.number_input(
                "Price per Share / Dividend per Share",
                min_value=0.0,
                value=0.0,
                step=1.0
            )

            fees = st.number_input(
                "Broker / DP / Other Charges",
                min_value=0.0,
                value=0.0,
                step=1.0
            )

            notes = st.text_input(
                "Notes",
                placeholder="Optional details"
            )

            submitted = st.form_submit_button(
                "Save Transaction",
                type="primary",
                use_container_width=True
            )

            if submitted:

                if not symbol_input.strip():
                    st.error("Enter a company symbol.")

                elif quantity <= 0:
                    st.error("Quantity must be greater than zero.")

                elif action in ["BUY", "SELL", "RIGHT"] and price <= 0:
                    st.error("Enter a valid share price.")

                else:

                    add_transaction(
                        trade_date,
                        symbol_input,
                        action,
                        quantity,
                        price,
                        fees,
                        notes
                    )

                    st.success("Transaction saved successfully.")
                    st.rerun()

        st.caption("""
        BUY = Purchase shares.
        SELL = Sell shares.
        BONUS = Bonus shares received.
        RIGHT = Right shares purchased.
        DIVIDEND = Cash dividend per share.
        ADJUSTMENT = Manual share quantity adjustment.
        """)

    # -----------------------------------------------------
    # HOLDINGS
    # -----------------------------------------------------

    with tab3:

        st.subheader("My Current Holdings")

        if not holdings_df.empty:

            st.dataframe(
                holdings_df.round(2),
                use_container_width=True,
                hide_index=True
            )

        else:
            st.info("No holdings available.")

    # -----------------------------------------------------
    # TRANSACTION HISTORY
    # -----------------------------------------------------

    with tab4:

        st.subheader("Transaction History")

        if not transactions.empty:

            st.dataframe(
                transactions,
                use_container_width=True,
                hide_index=True
            )

            st.warning(
                "Deleting a transaction changes all calculated "
                "portfolio balances. Check the record carefully."
            )

            transaction_ids = transactions["id"].tolist()

            selected_id = st.selectbox(
                "Select Transaction ID to Delete",
                transaction_ids
            )

            confirm_delete = st.checkbox(
                "I confirm that I want to delete this record."
            )

            if st.button("Delete Selected Transaction"):

                if confirm_delete:
                    delete_transaction(selected_id)
                    st.success("Transaction deleted.")
                    st.rerun()
                else:
                    st.error("Please confirm before deleting.")

        else:
            st.info("No transaction history.")

    # -----------------------------------------------------
    # REPORTS
    # -----------------------------------------------------

    with tab5:

        st.subheader("Portfolio Reports")

        report_data = {
            "Metric": [
                "Invested Cost",
                "Current Market Value",
                "Realized Profit/Loss",
                "Unrealized Profit/Loss",
                "Dividend Income",
                "Estimated Capital Gains Tax",
                "Estimated Total Profit/Loss"
            ],
            "Amount (Rs.)": [
                total_cost,
                market_value,
                realized_total,
                unrealized,
                dividend_total,
                estimated_tax,
                total_profit
            ]
        }

        report_df = pd.DataFrame(report_data)

        st.dataframe(
            report_df,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Download Portfolio Report CSV",
            report_df.to_csv(index=False).encode("utf-8"),
            file_name="nepse_edge_portfolio_report.csv",
            mime="text/csv"
        )

        if not transactions.empty:

            csv_data = transactions.to_csv(
                index=False
            ).encode("utf-8")

            st.download_button(
                "Download Transaction History CSV",
                csv_data,
                file_name="nepse_edge_transactions.csv",
                mime="text/csv"
            )


# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

elif page == "Settings":

    st.header("⚙️ Settings")

    st.subheader("Capital Gains Tax Settings")

    st.write(
        "Default rates are for a qualifying resident natural "
        "person selling listed shares. Verify the applicable "
        "rate and broker settlement statement for each sale."
    )

    short_tax = st.number_input(
        "Short-term CGT (%) - 365 days or less",
        min_value=0.0,
        max_value=100.0,
        value=float(get_setting("short_tax", 5.0)),
        step=0.25
    )

    long_tax = st.number_input(
        "Long-term CGT (%) - more than 365 days",
        min_value=0.0,
        max_value=100.0,
        value=float(get_setting("long_tax", 3.75)),
        step=0.25
    )

    if st.button("Save Tax Settings"):
        save_setting("short_tax", short_tax)
        save_setting("long_tax", long_tax)
        st.success("Tax settings saved.")

    st.divider()

    st.subheader("Data Source")

    st.write(
        "Market Data: YONEPSE public community data mirror."
    )

    st.caption(
        "This is not an official NEPSE application. "
        "Market information may be delayed or incomplete."
    )

    if st.button("Refresh Market Data"):
        st.cache_data.clear()
        st.rerun()

    st.divider()

    st.subheader("Portfolio Database Backup")

    if os.path.exists(DB_PATH):

        with open(DB_PATH, "rb") as file:
            db_bytes = file.read()

        st.download_button(
            "Download Portfolio Database Backup",
            db_bytes,
            file_name="nepse_edge_backup.db",
            mime="application/octet-stream"
        )

    uploaded_backup = st.file_uploader(
        "Restore Database Backup",
        type=["db"]
    )

    if uploaded_backup is not None:

        st.warning(
            "Restoring a backup replaces the current portfolio database."
        )

        confirm_restore = st.checkbox(
            "I understand that the current database will be replaced."
        )

        if st.button("Restore Backup"):

            if confirm_restore:

                with open(DB_PATH, "wb") as file:
                    file.write(uploaded_backup.getvalue())

                st.success("Database restored. Reloading application.")
                st.rerun()

            else:
                st.error("Please confirm before restoring.")


# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------

st.divider()

st.caption(
    "NEPSE EDGE | Personal Market Analysis & Portfolio Management"
)

st.caption(
    "Third-party data may be delayed or incomplete. "
    "Always verify market prices, financial reports, "
    "tax deductions and broker statements."
)
