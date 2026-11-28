import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
from urllib.parse import quote

try:
    from supabase import create_client
except Exception:
    create_client = None

st.set_page_config(page_title="NEPSE EDGE", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")
BASE = "https://raw.githubusercontent.com/Shubhamnpk/yonepse/main/data"
PAGES = ["📊 MARKET DASHBOARD", "🔍 STOCK SCANNER", "🏢 SECTOR EXPLORER", "📚 FUNDAMENTAL ANALYSIS", "📈 TECHNICAL ANALYSIS", "📰 NEWS INTELLIGENCE", "🧠 SMART RECOMMENDATIONS", "💼 WATCHLIST & PORTFOLIO"]

# Original NEPSE EDGE home card layout retained: 2 columns, 116px cards (108px on very small screens).
st.markdown("""
<style>
.stApp{width:100%;}.block-container{max-width:100%!important;padding:1rem .65rem 2rem .65rem!important;}
.edge-header{text-align:center;padding:8px 0 20px}.edge-logo{font-size:38px;font-weight:900;letter-spacing:2px;color:#2196F3}.edge-subtitle{font-size:12px;letter-spacing:1.5px;color:gray}
.section-heading{font-size:19px;font-weight:800;margin:12px 0}
div[data-testid="stHorizontalBlock"]{display:flex!important;flex-wrap:nowrap!important;gap:10px!important;width:100%!important}
div[data-testid="column"]{width:50%!important;min-width:0!important;flex:1 1 50%!important}
div.stButton>button{width:100%;height:116px;min-height:116px;max-height:116px;border-radius:16px;border:1px solid #64748b;background:rgba(100,116,139,.09);font-size:15px;font-weight:800;line-height:1.5;white-space:pre-line;text-align:center;padding:8px 3px;overflow-wrap:anywhere;box-shadow:0 2px 7px rgba(0,0,0,.08)}
div.stButton>button:hover{border:2px solid #2196F3;color:#2196F3;transform:translateY(-2px)}
.edge-footer{text-align:center;font-size:11px;color:gray;padding:20px 0}.small-note{font-size:12px;color:gray}
@media(max-width:380px){.block-container{padding-left:.4rem!important;padding-right:.4rem!important}div[data-testid="stHorizontalBlock"]{gap:7px!important}div.stButton>button{height:108px;min-height:108px;max-height:108px;font-size:13px}.edge-logo{font-size:32px}}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300, show_spinner=False)
def get_json(path):
    r = requests.get(f"{BASE}/{path}", timeout=20, headers={"User-Agent":"NEPSE-EDGE/2.0"})
    r.raise_for_status()
    return r.json()

def safe_list(path):
    try:
        x = get_json(path)
        return x if isinstance(x, list) else []
    except Exception:
        return []

def load_market():
    errors=[]
    try: prices=get_json("nepse_data.json")
    except Exception as e: prices=[]; errors.append("Price feed unavailable: "+str(e))
    try: securities=get_json("other/securities.json")
    except Exception as e: securities=[]; errors.append("Company directory unavailable: "+str(e))
    try: indices=get_json("market/indices.json")
    except Exception as e: indices=[]; errors.append("Indices unavailable: "+str(e))
    try: summary=get_json("market/summary.json")
    except Exception as e: summary=[]; errors.append("Market summary unavailable: "+str(e))
    try: tops=get_json("market/top_stocks.json")
    except Exception as e: tops={}; errors.append("Top stocks unavailable: "+str(e))
    p=pd.DataFrame(prices if isinstance(prices,list) else [])
    s=pd.DataFrame(securities if isinstance(securities,list) else [])
    if not p.empty and not s.empty and "symbol" in p and "symbol" in s:
        if "instrumentType" in s: s=s[s.instrumentType.astype(str).str.lower().eq("equity")]
        if "status" in s: s=s[s.status.astype(str).str.upper().eq("A")]
        keep=[c for c in ["symbol","companyName","securityName","sectorName"] if c in s.columns]
        df=p.merge(s[keep].drop_duplicates("symbol"),on="symbol",how="inner")
    else: df=p.copy()
    for c in ["ltp","previous_close","change","percent_change","high","low","volume","turnover","trades","market_cap"]:
        if c in df: df[c]=pd.to_numeric(df[c],errors="coerce")
    return df,indices,summary,tops,errors

def fmt(v, digits=2):
    try:
        if pd.isna(v): return "—"
        return f"{float(v):,.{digits}f}"
    except Exception: return "—"

def summary_value(summary, label):
    for item in summary if isinstance(summary,list) else []:
        if label.lower() in str(item.get("detail","")).lower(): return item.get("value","—")
    return "—"

def get_row(sym):
    if df.empty: return None
    z=df[df.symbol.astype(str).str.upper()==str(sym).upper()]
    return None if z.empty else z.iloc[0]

def stock_picker(key, label="कम्पनी छान्नुहोस्"):
    if not symbols:
        st.warning("कम्पनी सूची अहिले उपलब्ध छैन।")
        return None
    return st.selectbox(label, symbols, key=key)

def stock_overview(sym):
    r=get_row(sym)
    if r is None: st.warning("यस कम्पनीको मूल्य डाटा उपलब्ध छैन।"); return
    name=r.get("companyName",r.get("securityName",sym))
    st.subheader(f"{name} ({sym})")
    a,b,c,d=st.columns(4)
    a.metric("LTP (Rs.)",fmt(r.get("ltp")))
    b.metric("Change",fmt(r.get("change")),f"{fmt(r.get('percent_change'))}%")
    c.metric("Volume",fmt(r.get("volume"),0))
    d.metric("Turnover (Rs.)",fmt(r.get("turnover"),0))
    st.caption(f"Sector: {r.get('sectorName','Not available')}  •  Data timestamp: {r.get('last_updated','Not supplied by source')}")

def supabase_client():
    try:
        sec=st.secrets
        url=sec.get("SUPABASE_URL","")
        key=sec.get("SUPABASE_KEY",sec.get("SUPABASE_PUBLISHABLE_KEY",""))
        if url and key and create_client: return create_client(url,key)
    except Exception: pass
    return None

sb=supabase_client()
def portfolio_user():
    if not sb:
        st.error("Supabase connection भेटिएन। Streamlit → Manage app → Settings → Secrets मा SUPABASE_URL र SUPABASE_KEY जाँच्नुहोस्।")
        return None
    if st.session_state.get("sb_access") and st.session_state.get("sb_refresh"):
        try:
            sb.auth.set_session(st.session_state.sb_access,st.session_state.sb_refresh)
            return st.session_state.get("sb_user")
        except Exception:
            for k in ["sb_access","sb_refresh","sb_user"]: st.session_state.pop(k,None)
    st.markdown("#### Portfolio मा सुरक्षित प्रवेश")
    st.caption("Email OTP बाट लगइन गर्नुहोस्। Supabase Auth मा Email provider सक्रिय हुनुपर्छ।")
    email=st.text_input("तपाईंको Email",key="login_email")
    if st.button("Email OTP पठाउनुहोस्",key="send_otp"):
        try:
            sb.auth.sign_in_with_otp({"email":email})
            st.session_state.otp_email=email
            st.success("Email मा आएको OTP जाँच्नुहोस्।")
        except Exception as e: st.error(f"OTP पठाउन सकिएन: {e}")
    if st.session_state.get("otp_email"):
        otp=st.text_input("Email मा आएको OTP",key="login_otp")
        if st.button("OTP Verify / Login",key="verify_otp"):
            try:
                res=sb.auth.verify_otp({"email":st.session_state.otp_email,"token":otp,"type":"email"})
                st.session_state.sb_access=res.session.access_token
                st.session_state.sb_refresh=res.session.refresh_token
                st.session_state.sb_user=res.user.id
                st.rerun()
            except Exception as e: st.error(f"OTP मिलेन: {e}")
    return None

def get_transactions(uid):
    try:
        return sb.table("portfolio_transactions").select("*").eq("user_id",uid).order("transaction_date").order("id").execute().data or []
    except Exception as e:
        st.error(f"Database बाट कारोबार पढ्न सकिएन: {e}")
        return []

def calc_holdings(transactions):
    rows=[]
    if not transactions: return pd.DataFrame()
    tdf=pd.DataFrame(transactions)
    for sym,part in tdf.groupby("symbol"):
        part=part.sort_values(["transaction_date","id"])
        qty=0; cost=0.0; realized=0.0; bought=0; sold=0
        for _,t in part.iterrows():
            q=int(t["quantity"]); price=float(t["price"])
            if t["transaction_type"]=="BUY":
                qty+=q; cost+=q*price; bought+=q
            else:
                if qty>0:
                    avg=cost/qty
                    realized+=(price-avg)*q
                    cost-=avg*q; qty-=q; sold+=q
        avg=cost/qty if qty else 0
        r=get_row(sym); ltp=float(r["ltp"]) if r is not None and pd.notna(r.get("ltp")) else np.nan
        rows.append({"Symbol":sym,"Bought Qty":bought,"Sold Qty":sold,"Balance":qty,"Avg Cost (Rs.)":round(avg,2),"LTP (Rs.)":round(ltp,2) if pd.notna(ltp) else None,"Invested Cost (Rs.)":round(cost,2),"Unrealized P/L (Rs.)":round((ltp-avg)*qty,2) if pd.notna(ltp) else None,"Realized P/L (Rs.)":round(realized,2)})
    return pd.DataFrame(rows)

# Fetch source data once; each endpoint fails independently.
with st.spinner("NEPSE बजार डाटा लोड हुँदैछ..."):
    df,indices,summary,tops,errors=load_market()
symbols=sorted(df.symbol.dropna().astype(str).unique().tolist()) if not df.empty and "symbol" in df else []
if "page" not in st.session_state: st.session_state.page="Home"
if "watchlist" not in st.session_state: st.session_state.watchlist=[]

st.markdown('<div class="edge-header"><div class="edge-logo">NEPSE EDGE</div><div class="edge-subtitle">NEPAL STOCK MARKET INTELLIGENCE</div></div>',unsafe_allow_html=True)
with st.sidebar:
    st.title("NEPSE EDGE")
    if st.button("🏠 HOME",use_container_width=True): st.session_state.page="Home"
    for p in PAGES:
        if st.button(p,use_container_width=True): st.session_state.page=p
    st.caption("Public YONEPSE data mirror • Not official NEPSE tick-by-tick data")

# HOME — preserve the original eight square cards and their positions.
if st.session_state.page=="Home":
    st.markdown('<div class="section-heading">Explore NEPSE EDGE</div>',unsafe_allow_html=True)
    for i in range(0,8,2):
        a,b=st.columns(2,gap="small")
        with a:
            if st.button(PAGES[i],key=f"home_{i}"): st.session_state.page=PAGES[i]
        with b:
            if st.button(PAGES[i+1],key=f"home_{i+1}"): st.session_state.page=PAGES[i+1]
    st.markdown("### Market Snapshot")
    a,b=st.columns(2); a.metric("Total Turnover (Rs.)",summary_value(summary,"Total Turnover")); b.metric("Traded Shares",summary_value(summary,"Total Traded Shares"))
    a,b=st.columns(2); a.metric("Transactions",summary_value(summary,"Total Transactions")); b.metric("Scrips Traded",summary_value(summary,"Total Scrips Traded"))
    if indices:
        main=next((x for x in indices if str(x.get("index","")).lower()=="nepse index"),None)
        if main:
            a,b=st.columns(2); a.metric("NEPSE Index",fmt(main.get("currentValue",main.get("close"))),f"{fmt(main.get('perChange'))}%")
            b.metric("Market Capitalization",summary_value(summary,"Total Market Capitalization"))
    st.caption("डाटा सार्वजनिक YONEPSE mirror बाट हो; अपडेट ढिलो हुन सक्छ।")
    if errors: st.warning("केही डाटा स्रोत उपलब्ध भएनन्: "+" | ".join(errors))

elif st.session_state.page==PAGES[0]:
    st.title("📊 Market Dashboard")
    if indices:
        st.subheader("Market Indices")
        st.dataframe(pd.DataFrame(indices),use_container_width=True,hide_index=True)
    a,b,c=st.columns(3); a.metric("Turnover",summary_value(summary,"Total Turnover")); b.metric("Traded Shares",summary_value(summary,"Total Traded Shares")); c.metric("Transactions",summary_value(summary,"Total Transactions"))
    if not df.empty:
        ch=df.get("change",pd.Series(0,index=df.index)).fillna(0)
        a,b,c=st.columns(3); a.metric("Advancers",int((ch>0).sum())); b.metric("Decliners",int((ch<0).sum())); c.metric("Unchanged",int((ch==0).sum()))
        left,right=st.columns(2)
        with left:
            st.subheader("Top Gainers"); st.dataframe(df.sort_values("percent_change",ascending=False).head(10)[[c for c in ["symbol","companyName","ltp","percent_change","volume"] if c in df]],use_container_width=True,hide_index=True)
        with right:
            st.subheader("Top Losers"); st.dataframe(df.sort_values("percent_change").head(10)[[c for c in ["symbol","companyName","ltp","percent_change","volume"] if c in df]],use_container_width=True,hide_index=True)
        st.subheader("Highest Turnover")
        st.dataframe(df.sort_values("turnover",ascending=False).head(10)[[c for c in ["symbol","companyName","ltp","turnover","volume"] if c in df]],use_container_width=True,hide_index=True)
        if "sectorName" in df:
            sec=df.groupby("sectorName",dropna=True).agg(Companies=("symbol","count"),AvgChange=("percent_change","mean"),Turnover=("turnover","sum")).reset_index().sort_values("Turnover",ascending=False)
            st.subheader("Sector Overview")
            st.plotly_chart(px.bar(sec,x="sectorName",y="Turnover",title="Sector turnover (Rs.)"),use_container_width=True)
            st.dataframe(sec,use_container_width=True,hide_index=True)
        st.subheader("All Traded Equities")
        st.dataframe(df.sort_values("turnover",ascending=False),use_container_width=True,hide_index=True)
    else: st.error("बजार मूल्य डाटा उपलब्ध छैन।")

elif st.session_state.page==PAGES[1]:
    st.title("🔍 Stock Scanner")
    q=st.text_input("कम्पनीको नाम वा Symbol खोज्नुहोस्")
    sector_list=sorted(df.sectorName.dropna().astype(str).unique()) if not df.empty and "sectorName" in df else []
    sector=st.selectbox("Sector Filter",["All Sectors"]+sector_list)
    min_change=st.slider("Minimum daily change (%)",-20.0,20.0,0.0,0.5)
    if not df.empty:
        v=df.copy()
        if q: v=v[v.astype(str).apply(lambda c:c.str.contains(q,case=False,na=False)).any(axis=1)]
        if sector!="All Sectors" and "sectorName" in v: v=v[v.sectorName.astype(str)==sector]
        if "percent_change" in v: v=v[v.percent_change.fillna(-999)>=min_change]
        st.write(f"नतिजा: {len(v)} कम्पनी")
        cols=[c for c in ["symbol","companyName","sectorName","ltp","change","percent_change","high","low","volume","turnover","trades","last_updated"] if c in v]
        st.dataframe(v[cols].sort_values("turnover",ascending=False) if "turnover" in cols else v[cols],use_container_width=True,hide_index=True)
        if not v.empty:
            chosen=st.selectbox("कम्पनीको विस्तृत विवरण खोल्नुहोस्",v.symbol.astype(str).tolist(),key="scanner_detail")
            if st.button("Open Company Analysis",key="open_scan_company"):
                st.session_state.company_to_open=chosen; st.session_state.page=PAGES[3]; st.rerun()
    else: st.warning("कम्पनी डाटा उपलब्ध छैन।")

elif st.session_state.page==PAGES[2]:
    st.title("🏢 Sector Explorer")
    if not df.empty and "sectorName" in df:
        sectors=sorted(df.sectorName.dropna().astype(str).unique())
        sector=st.selectbox("Sector छान्नुहोस्",["All Sectors"]+sectors)
        q=st.text_input("Sector भित्र कम्पनी खोज्नुहोस्")
        v=df.copy() if sector=="All Sectors" else df[df.sectorName.astype(str)==sector].copy()
        if q: v=v[v.astype(str).apply(lambda c:c.str.contains(q,case=False,na=False)).any(axis=1)]
        st.subheader(f"{sector} — {len(v)} कम्पनी")
        st.dataframe(v.sort_values("turnover",ascending=False),use_container_width=True,hide_index=True)
        if not v.empty:
            sym=st.selectbox("कम्पनी छान्नुहोस्",v.symbol.astype(str).tolist(),key="sector_company")
            stock_overview(sym)
    else: st.warning("Sector classification उपलब्ध छैन।")

elif st.session_state.page==PAGES[3]:
    st.title("📚 Fundamental Analysis")
    st.caption("कम्पनीको उपलब्ध market snapshot र fundamental due-diligence checklist")
    default=st.session_state.pop("company_to_open",None)
    if default in symbols:
        idx=symbols.index(default)
        sym=st.selectbox("कम्पनी छान्नुहोस्",symbols,index=idx,key="fundamental_company")
    else: sym=stock_picker("fundamental_company")
    if sym:
        stock_overview(sym); r=get_row(sym)
        st.subheader("Fundamental Data Availability")
        st.warning("हाल जडान भएको सार्वजनिक YONEPSE feed मा audited EPS, P/E, book value, quarterly net profit, debt/equity र cash-flow statements समावेश छैनन्। ती वित्तीय तथ्यांक अनुमान गरेर देखाइएको छैन।")
        a,b=st.columns(2)
        with a:
            st.markdown("**जाँच्नुपर्ने मुख्य सूचकहरू**")
            for item in ["EPS र EPS growth","P/E ratio (sector comparison सहित)","Book value र P/B ratio","Net profit र operating profit trend","Debt-to-equity र interest coverage","Cash flow from operations","Dividend history र payout ratio"]: st.write("• "+item)
        with b:
            st.markdown("**हाल उपलब्ध कम्पनी विवरण**")
            st.write("Sector: "+str(r.get("sectorName","—")))
            st.write("Market Cap: "+fmt(r.get("market_cap")))
            st.write("LTP: Rs. "+fmt(r.get("ltp")))
            st.write("52-week range: स्रोतले यस feed मा नदिएको हुन सक्छ।")
        st.markdown("**प्रमाणित रिपोर्ट खोज्ने स्रोतहरू**")
        st.markdown(f"- [NEPSE official website](https://www.nepalstock.com/)\n- [ShareSansar — {sym} खोज्नुहोस्](https://www.sharesansar.com/company/{quote(sym)})\n- [Company disclosure / investor relations खोज्नुहोस्](https://www.google.com/search?q={quote(sym+' Nepal quarterly report')})")
        st.caption("कम्पनीको PDF quarterly report अपलोड गरेमा त्यसको EPS, profit, debt र ratios छुट्टै विश्लेषण गर्न सकिन्छ।")

elif st.session_state.page==PAGES[4]:
    st.title("📈 Technical Analysis")
    st.caption("Indicators गणना गर्न ऐतिहासिक daily price series चाहिन्छ। उपलब्ध snapshot बाट ऐतिहासिक RSI/MACD बनाइएको छैन।")
    sym=stock_picker("technical_company")
    if sym:
        stock_overview(sym); r=get_row(sym)
        st.subheader("Latest Price Snapshot Chart")
        vals={k:r.get(k) for k in ["ltp","previous_close","high","low"]}
        chart=pd.DataFrame({"Price Type":list(vals.keys()),"Price (Rs.)":[pd.to_numeric(v,errors="coerce") for v in vals.values()]})
        chart=chart.dropna()
        if not chart.empty:
            st.plotly_chart(px.bar(chart,x="Price Type",y="Price (Rs.)",title=f"{sym} — available session price levels"),use_container_width=True)
        st.info("यो एउटै कारोबार दिनको price snapshot हो, historical line/candlestick chart होइन। RSI, MACD, EMA, SMA, Bollinger Bands र ATR सही निकाल्न धेरै दिनको OHLC history चाहिन्छ।")
        st.subheader("Technical Indicator Guide")
        indicator_help=pd.DataFrame([
            ["RSI (14)","Momentum / overbought-oversold","14+ daily closes"],
            ["MACD (12,26,9)","Trend momentum / crossover","26+ daily closes"],
            ["EMA 20 / 50 / 200","Short, medium, long trend","50–200+ daily closes"],
            ["SMA 20 / 50 / 200","Average price trend","20–200+ daily closes"],
            ["Bollinger Bands (20,2)","Volatility / band expansion","20+ daily closes"],
            ["ATR / ADX","Volatility / trend strength","OHLC candles required"]],columns=["Indicator","What it measures","Minimum input"])
        st.dataframe(indicator_help,use_container_width=True,hide_index=True)
        st.markdown(f"[Search {sym} historical chart](https://www.google.com/search?q={quote(sym+' NEPSE historical price chart')})")
        upload=st.file_uploader("ऐतिहासिक OHLC CSV भए यहाँ अपलोड गर्नुहोस् (Date, Open, High, Low, Close, Volume columns)",type=["csv"],key="ohlc_upload")
        if upload:
            try:
                h=pd.read_csv(upload); h.columns=[str(c).strip().title() for c in h.columns]
                required={"Date","Open","High","Low","Close"}
                if not required.issubset(set(h.columns)): st.error("CSV मा Date, Open, High, Low, Close columns अनिवार्य छन्।")
                else:
                    h["Date"]=pd.to_datetime(h["Date"],errors="coerce"); h=h.dropna(subset=["Date","Close"]).sort_values("Date")
                    for c in ["Open","High","Low","Close"]: h[c]=pd.to_numeric(h[c],errors="coerce")
                    h["EMA20"]=h.Close.ewm(span=20,adjust=False).mean(); h["SMA20"]=h.Close.rolling(20).mean()
                    delta=h.Close.diff(); gain=delta.clip(lower=0).rolling(14).mean(); loss=-delta.clip(upper=0).rolling(14).mean(); rs=gain/loss.replace(0,np.nan); h["RSI14"]=100-(100/(1+rs))
                    e12=h.Close.ewm(span=12,adjust=False).mean(); e26=h.Close.ewm(span=26,adjust=False).mean(); h["MACD"]=e12-e26; h["Signal"]=h.MACD.ewm(span=9,adjust=False).mean()
                    fig=go.Figure(); fig.add_trace(go.Candlestick(x=h.Date,open=h.Open,high=h.High,low=h.Low,close=h.Close,name="Price")); fig.add_trace(go.Scatter(x=h.Date,y=h.EMA20,name="EMA 20")); fig.add_trace(go.Scatter(x=h.Date,y=h.SMA20,name="SMA 20")); st.plotly_chart(fig,use_container_width=True)
                    a,b=st.columns(2); a.metric("Latest RSI 14",fmt(h.RSI14.iloc[-1])); b.metric("Latest MACD",fmt(h.MACD.iloc[-1]))
                    st.plotly_chart(px.line(h,x="Date",y=["RSI14"],title="RSI (14)"),use_container_width=True)
                    st.plotly_chart(px.line(h,x="Date",y=["MACD","Signal"],title="MACD"),use_container_width=True)
                    st.success(f"Uploaded historical series analyzed: {len(h)} rows. यो अपलोड गरिएको फाइलमा आधारित विश्लेषण हो।")
            except Exception as e: st.error(f"CSV पढ्न सकिएन: {e}")

elif st.session_state.page==PAGES[5]:
    st.title("📰 News Intelligence")
    st.caption("कम्पनी र बजारका समाचार/सूचना खोज्न प्रमाणित स्रोतका लिंक। हाल प्रत्यक्ष news API जोडिएको छैन।")
    tab1,tab2=st.tabs(["Market News & Notices","Company News"])
    with tab1:
        st.markdown("- [NEPSE official notices and disclosures](https://www.nepalstock.com/)\n- [SEBON notices](https://www.sebon.gov.np/)\n- [ShareSansar News](https://www.sharesansar.com/)\n- [Merolagani News](https://merolagani.com/NewsList.aspx)\n- [Nepal economic news](https://www.google.com/search?q=Nepal+stock+market+NEPSE+latest+news)")
    with tab2:
        sym=stock_picker("news_company","कम्पनी छान्नुहोस्")
        if sym:
            r=get_row(sym); st.subheader(f"{r.get('companyName',sym)} ({sym}) — Company News")
            st.markdown(f"- [ShareSansar company page](https://www.sharesansar.com/company/{quote(sym)})\n- [Company-specific NEPSE news search](https://www.google.com/search?q={quote(sym+' NEPSE news disclosure')})\n- [Quarterly report search](https://www.google.com/search?q={quote(sym+' Nepal quarterly report')})\n- [Dividend / AGM / book closure search](https://www.google.com/search?q={quote(sym+' dividend AGM book closure Nepal')})")
            st.warning("यी स्रोतमा जाने खोजी लिंक हुन्; एपले अहिले समाचार स्वतः सङ्कलन गरेर देखाउँदैन। समाचारको मिति र स्रोत जाँचेर मात्र निर्णय गर्नुहोस्।")

elif st.session_state.page==PAGES[6]:
    st.title("🧠 Smart Recommendations")
    st.caption("Market snapshot आधारित preliminary screening — audited fundamentals, historical indicators र news पुष्टि नभएसम्म BUY सिफारिस दिइँदैन।")
    n=st.select_slider("कति कम्पनी देखाउने?",options=[5,8,10,15,20,30],value=10)
    if not df.empty:
        x=df.copy(); x["Score / 100"]=0.0; x["Coverage %"]=0.0; x["Signal"]="INSUFFICIENT DATA"; x["Reason"]="Historical technical, fundamental र verified news data उपलब्ध छैन।"
        # Conservative, explainable score only for fields actually present; confidence is separate.
        scored=[]
        for _,r in x.iterrows():
            score=0.0; available=0.0; reasons=[]
            if pd.notna(r.get("percent_change")):
                available+=20
                score+=10 if r.get("percent_change")>0 else (5 if r.get("percent_change")==0 else 0)
                if r.get("percent_change")>0: reasons.append("आजको परिवर्तन सकारात्मक")
            if pd.notna(r.get("volume")) and r.get("volume")>0: available+=10; score+=5; reasons.append("कारोबार भएको volume")
            if pd.notna(r.get("turnover")) and r.get("turnover")>0: available+=10; score+=5; reasons.append("कारोबार भएको turnover")
            if pd.notna(r.get("ltp")) and pd.notna(r.get("previous_close")) and r.get("previous_close")>0:
                available+=10
                if r.get("ltp")>=r.get("previous_close"): score+=5
            scored.append({"Symbol":r.get("symbol"),"Company":r.get("companyName",r.get("securityName","")),"Sector":r.get("sectorName","—"),"Preliminary Points":round(score,1),"Verified Input Coverage":round(available,1),"Signal":"WATCH — NOT A BUY CALL","Available evidence":"; ".join(reasons) or "No positive evidence"})
        rec=pd.DataFrame(scored).sort_values(["Preliminary Points","Verified Input Coverage"],ascending=False).head(n)
        st.dataframe(rec,use_container_width=True,hide_index=True)
        st.error("अहिले उपलब्ध feed बाट भरपर्दो 100-point Buy score निकाल्न सकिँदैन। यहाँको अंक पूर्ण recommendation होइन। Historical OHLC + financial statements + dated company news + backtesting नहुँदासम्म कुनै stock लाई Strong Buy भनिँदैन।")
        st.markdown("**पूर्ण recommendation model को भार:** Technical 35% • Fundamental 30% • Price Action/Momentum 20% • Risk 10% • Liquidity 5%. कुनै input नआएमा score लाई उपलब्ध input अनुसार मात्र देखाइनेछ र confidence घटाइनेछ।")
    else: st.warning("Market data unavailable.")

elif st.session_state.page==PAGES[7]:
    st.title("💼 Watchlist & Portfolio")
    st.subheader("My Watchlist")
    sym=stock_picker("watch_company")
    if sym and st.button("＋ Add to Watchlist",key="add_watch"):
        if sym not in st.session_state.watchlist: st.session_state.watchlist.append(sym)
    if st.session_state.watchlist:
        st.dataframe(df[df.symbol.astype(str).isin(st.session_state.watchlist)][[c for c in ["symbol","companyName","ltp","percent_change","turnover"] if c in df]],use_container_width=True,hide_index=True)
    st.divider(); st.subheader("Buy / Sell Transaction Ledger")
    uid=portfolio_user()
    if uid:
        with st.form("tx_form",clear_on_submit=True):
            a,b=st.columns(2)
            with a: txsym=st.selectbox("Company / Symbol",symbols if symbols else [""],key="tx_symbol")
            with b: typ=st.selectbox("Transaction Type",["BUY","SELL"],key="tx_type")
            c,d,e=st.columns(3)
            with c: qty=st.number_input("Quantity",min_value=1,step=1,value=10)
            with d: price=st.number_input("Price per share (Rs.)",min_value=0.01,step=0.5,value=100.0)
            with e: txdate=st.date_input("Transaction Date",value=date.today())
            notes=st.text_input("Notes (optional)")
            save=st.form_submit_button("Save Buy / Sell Transaction")
        tx=get_transactions(uid)
        if save:
            try:
                held=0
                for t in tx:
                    if t["symbol"]==txsym: held += int(t["quantity"]) if t["transaction_type"]=="BUY" else -int(t["quantity"])
                if typ=="SELL" and qty>held: st.error(f"बिक्री गर्न मिल्दैन: {txsym} मा {held} कित्ता मात्र बाँकी छ।")
                elif not txsym: st.error("कम्पनी छान्नुहोस्।")
                else:
                    sb.table("portfolio_transactions").insert({"user_id":uid,"symbol":txsym,"transaction_type":typ,"quantity":int(qty),"price":float(price),"transaction_date":str(txdate),"notes":notes}).execute()
                    st.success("कारोबार Supabase मा सुरक्षित भयो।"); st.rerun()
            except Exception as e: st.error(f"Save असफल: {e}")
        tx=get_transactions(uid)
        if tx:
            holdings=calc_holdings(tx)
            if not holdings.empty:
                st.subheader("Current Holdings & Profit / Loss")
                st.dataframe(holdings,use_container_width=True,hide_index=True)
                realized=pd.to_numeric(holdings["Realized P/L (Rs.)"],errors="coerce").sum()
                unreal=pd.to_numeric(holdings["Unrealized P/L (Rs.)"],errors="coerce").sum()
                a,b=st.columns(2); a.metric("Total Realized P/L",f"Rs. {realized:,.2f}"); b.metric("Total Unrealized P/L",f"Rs. {unreal:,.2f}")
            st.subheader("Complete Transaction History")
            tdf=pd.DataFrame(tx).sort_values(["transaction_date","id"],ascending=False)
            st.dataframe(tdf,use_container_width=True,hide_index=True)
        else: st.info("अहिलेसम्म Buy/Sell कारोबार थपिएको छैन।")
        if st.button("Logout from Portfolio",key="logout"):
            for k in ["sb_access","sb_refresh","sb_user","otp_email"]: st.session_state.pop(k,None)
            st.rerun()

st.markdown('<div class="edge-footer">NEPSE EDGE © 2026<br/>INDEPENDENT STOCK MARKET INTELLIGENCE PLATFORM</div>',unsafe_allow_html=True)
