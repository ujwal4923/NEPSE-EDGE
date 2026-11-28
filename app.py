
import streamlit as st
import pandas as pd
import urllib.request
import json

st.set_page_config(
    page_title="NEPSE EDGE",
    page_icon="📈",
    layout="wide"
)

BASE = "https://raw.githubusercontent.com/Shubhamnpk/yonepse/main/data"

@st.cache_data(ttl=300)
def get_data(path):
    url = BASE + "/" + path
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "NEPSE-EDGE"}
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))

st.title("📈 NEPSE EDGE")
st.caption("Full NEPSE Market Intelligence & Stock Scanner")

st.info(
    "Data source: YONEPSE public data mirror. "
    "Not an official NEPSE application."
)

try:
    data = get_data("nepse_data.json")

    if not isinstance(data, list) or len(data) == 0:
        st.error("Market data is empty or unavailable.")
        st.stop()

    df = pd.DataFrame(data)

    # Load security information
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
        st.warning(
            "Security classification unavailable. "
            "Showing available market records."
        )

    # Remove open-ended mutual fund records
    if "asset_type" in df.columns:
        df = df[
            df["asset_type"].astype(str).str.lower()
            != "open_ended_mutual_fund"
        ]

    # Prefer ordinary equity securities
    if "instrumentType" in df.columns:
        equity = df[
            df["instrumentType"].astype(str).str.lower()
            == "equity"
        ]
        if not equity.empty:
            df = equity

    # Convert numerical columns
    numeric = [
        "ltp", "change", "percent_change",
        "volume", "turnover", "high", "low"
    ]

    for col in numeric:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col], errors="coerce"
            )

    if "symbol" in df.columns:
        df = df.drop_duplicates("symbol")

    st.success(
        f"Market data loaded: {len(df)} securities"
    )

    # Market overview
    c1, c2, c3 = st.columns(3)

    c1.metric("Listed Securities", len(df))

    if "volume" in df.columns:
        c2.metric(
            "Total Volume",
            f"{df['volume'].fillna(0).sum():,.0f}"
        )

    if "turnover" in df.columns:
        c3.metric(
            "Total Turnover",
            f"Rs. {df['turnover'].fillna(0).sum():,.0f}"
        )

    st.divider()

    # Search
    st.subheader("🔎 Smart Stock Scanner")

    search = st.text_input(
        "Search Company or Symbol",
        placeholder="Example: NABIL"
    )

    filtered = df.copy()

    if search:
        mask = (
            filtered["symbol"].astype(str).str.contains(
                search, case=False, na=False
            )
            |
            filtered["name"].astype(str).str.contains(
                search, case=False, na=False
            )
        )
        filtered = filtered[mask]

    # Sector filter
    if "sectorName" in filtered.columns:
        sectors = sorted(
            filtered["sectorName"].dropna().unique().tolist()
        )
        if sectors:
            selected = st.selectbox(
                "Select Sector",
                ["All Sectors"] + sectors
            )
            if selected != "All Sectors":
                filtered = filtered[
                    filtered["sectorName"] == selected
                ]

    # Sort
    sort_options = {
        "Top Gainers": "percent_change",
        "Top Losers": "percent_change",
        "Highest Volume": "volume",
        "Highest Turnover": "turnover"
    }

    sort_choice = st.selectbox(
        "Sort Market Data",
        list(sort_options.keys())
    )

    if sort_choice == "Top Losers":
        filtered = filtered.sort_values(
            "percent_change", ascending=True,
            na_position="last"
        )
    else:
        filtered = filtered.sort_values(
            sort_options[sort_choice],
            ascending=False,
            na_position="last"
        )

    columns = [
        "symbol", "name", "ltp", "change",
        "percent_change", "volume", "turnover"
    ]

    if "sectorName" in filtered.columns:
        columns.append("sectorName")

    columns = [
        c for c in columns if c in filtered.columns
    ]

    st.dataframe(
        filtered[columns],
        use_container_width=True,
        hide_index=True
    )

    # Top gainers and losers
    st.divider()
    st.subheader("📊 Market Opportunities")

    if "percent_change" in df.columns:
        left, right = st.columns(2)

        with left:
            st.markdown("**Top 10 Gainers**")
            st.dataframe(
                df.nlargest(10, "percent_change")[
                    ["symbol", "ltp", "percent_change"]
                ],
                use_container_width=True,
                hide_index=True
            )

        with right:
            st.markdown("**Top 10 Losers**")
            st.dataframe(
                df.nsmallest(10, "percent_change")[
                    ["symbol", "ltp", "percent_change"]
                ],
                use_container_width=True,
                hide_index=True
            )

    if "last_updated" in df.columns:
        st.caption(
            "Source data timestamp: "
            + str(df["last_updated"].max())
        )

    st.caption(
        "Data is provided by a third-party community source. "
        "It may be delayed or incomplete. Verify prices "
        "before making investment decisions."
    )

    if st.button("🔄 Refresh Market Data"):
        st.cache_data.clear()
        st.rerun()

except Exception as e:
    st.error("Unable to load market data.")
    st.write("Technical details:", str(e))
    st.info(
        "Please try again later. The external data "
        "source may be temporarily unavailable."
    )

# MARKET BREADTH OVERVIEW
if "df" in globals() and not df.empty:
    st.divider()
    st.subheader("🌐 Market Overview")

    if "percent_change" in df.columns:
        advances = int((df["percent_change"] > 0).sum())
        declines = int((df["percent_change"] < 0).sum())
        unchanged = int((df["percent_change"] == 0).sum())

        c1, c2, c3 = st.columns(3)
        c1.metric("Advances", advances)
        c2.metric("Declines", declines)
        c3.metric("Unchanged", unchanged)

        breadth = pd.DataFrame({
            "Market Status": ["Advances", "Declines", "Unchanged"],
            "Securities": [advances, declines, unchanged]
        }).set_index("Market Status")

        st.bar_chart(breadth)
    else:
        st.info("Change percentage data is not available.")

    st.caption("Based on available market data. Security classification may be incomplete.")


# NEPSE INDEX DASHBOARD
try:
    index_data = get_data("market/indices.json")

    st.divider()
    st.header("📊 NEPSE Index Dashboard")

    if index_data:
        index_df = pd.DataFrame(index_data)

        for _, item in index_df.iterrows():
            st.subheader(item.get("index", "Market Index"))

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Current Value",
                round(float(item.get("close", 0)), 2),
                round(float(item.get("change", 0)), 2)
            )

            col2.metric(
                "Change %",
                f'{float(item.get("perChange", 0)):.2f}%'
            )

            col3.metric(
                "Previous Close",
                round(float(item.get("previousClose", 0)), 2)
            )

            st.caption(
                f'Updated: {item.get("generatedTime", "Not available")}'
            )
    else:
        st.warning("Index data is currently unavailable.")

except Exception as e:
    st.warning("NEPSE Index data is temporarily unavailable.")
