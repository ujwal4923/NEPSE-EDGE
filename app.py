import streamlit as st
import pandas as pd
import requests
import numpy as np
import plotly.graph_objects as go
from datetime import date
from supabase import create_client

st.set_page_config(page_title="NEPSE EDGE", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")
BASE = "https://raw.githubusercontent.com/Shubhamnpk/yonepse/main/data"

# Keep the original NEPSE EDGE home-card dimensions and two-column layout.
st.markdown("""
<style>
.stApp {width:100%;}
.block-container {max-width:100% !important;padding:1rem .65rem 2rem .65rem !important;}
.edge-header{text-align:center;padding:8px 0 20px;}
.edge-logo{font-size:38px;font-weight:900;letter-spacing:2px;color:#2196F3;}
.edge-subtitle{font-size:12px;letter-spacing:1.5px;color:gray;}
.section-heading{font-size:19px;font-weight:800;margin:12px 0;}
div[data-testid="stHorizontalBlock"]{display:flex!important;flex-wrap:nowrap!important;gap:10px!important;width:100%!important;}
div[data-testid="column"]{width:50%!important;min-width:0!important;flex:1 1 50%!important;}
div.stButton>button{width:100%;height:116px;min-height:116px;max-height:116px;border-radius:16px;border:1px solid #64748b;background:rgba(100,116,139,.09);font-size:15px;font-weight:800;line-height:1.5;white-space:pre-line;text-align:center;padding:8px 3px;overflow-wrap:anywhere;box-shadow:0 2px 7px rgba(0,0,0,.08);}
div.stButton>button:hover{border:2px solid #2196F3;color:#2196F3;transform:translateY(-2px);}
.edge-footer{text-align:center;font-size:11px;color:gray;padding:20px 0;}
.small-note{font-size:12px;color:gray;}
@media(max-width:380px){.block-container{padding-left:.4rem!important;padding-right:.4rem!important;}div[data-testid="stHorizontalBlock"]{gap:7px!important;}div.stButton>button{height:108px;min-height:108px;max-height:108px;font-size:13px;}.edge-logo{font-size:32px;}}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300, show_spinner=False)
def get_json(path):
    r=requests.get(f"{BASE}/{path}", timeout=18, headers={"User-Agent":"NEPSE-EDGE/1.0"})
    r.raise_for_status(); return r.json()

def load_market():
    problems=[]
    try: prices=get_json("nepse_data.json")
    except Exception as e: prices=[]; problems.append(f"Price feed: {e}")
    try: securities=get_json("other/securities.json")
    except Exception as e: securities=[]; problems.append(f"Securities: {e}")
    try: indices=get_json("market/indices.json")
    except Exception as e: indices=[]; problems.append(f"Indices: {e}")
    try: summary=get_json("market/summary.json")
    except Exception as e: summary=[]; problems.append(f"Summary: {e}")
    try: tops=get_json("market/top_stocks.json")
    except Exception as e: tops={}; problems.append(f"Top stocks: {e}")
    p=pd.DataFrame(prices if isinstance(prices,list) else [])
    s=pd.DataFrame(securities if isinstance(securities,list) else [])
    if not p.empty and not s.empty and 'symbol' in p and 'symbol' in s:
        if 'instrumentType' in s: s=s[s.instrumentType.astype(str).str.lower().eq('equity')]
        if 'status' in s: s=s[s.status.astype(str).str.upper().eq('A')]
        keep=[c for c in ['symbol','companyName','sectorName'] if c in s.columns]
        df=p.merge(s[keep].drop_duplicates('symbol'),on='symbol',how='inner')
    else: df=p.copy()
    for c in ['ltp','previous_close','change','percent_change','high','low','volume','turnover','trades','market_cap']:
        if c in df: df[c]=pd.to_numeric(df[c],errors='coerce')
    return df,indices,summary,tops,problems

def fmt(v):
    try:return f"{float(v):,.2f}"
    except:return "—"

def metric(label,value,delta=None):
    st.metric(label,value,delta)

def supabase_client():
    try:
        url=st.secrets.get("SUPABASE_URL","")
        key=st.secrets.get("SUPABASE_KEY","")
        if url and key: return create_client(url,key)
    except Exception: pass
    return None

sb=supabase_client()

def portfolio_login():
    if not sb:
        st.error("Supabase secrets भेटिएनन्। Streamlit Secrets मा SUPABASE_URL र SUPABASE_KEY जाँच्नुहोस्।")
        return None
    if st.session_state.get("sb_access") and st.session_state.get("sb_refresh"):
        try:
            sb.auth.set_session(st.session_state.sb_access,st.session_state.sb_refresh)
            return st.session_state.get("sb_user")
        except Exception:
            st.session_state.pop("sb_access",None); st.session_state.pop("sb_refresh",None)
    st.write("Portfolio सुरक्षित गर्न आफ्नो email बाट OTP login गर्नुहोस्।")
    email=st.text_input("Email address",key="portfolio_email")
    if st.button("Send login code"):
        try:
            sb.auth.sign_in_with_otp({"email":email})
            st.session_state["otp_email"]=email
            st.success("Email मा आएको OTP code हेर्नुहोस्।")
        except Exception as e: st.error(f"OTP पठाउन सकिएन: {e}")
    if st.session_state.get("otp_email"):
        otp=st.text_input("Email OTP code",key="portfolio_otp")
        if st.button("Verify OTP"):
            try:
                res=sb.auth.verify_otp({"email":st.session_state.otp_email,"token":otp,"type":"email"})
                st.session_state["sb_access"]=res.session.access_token
                st.session_state["sb_refresh"]=res.session.refresh_token
                st.session_state["sb_user"]=res.user.id
                st.rerun()
            except Exception as e: st.error(f"OTP verify भएन: {e}")
    return None

def get_transactions(user_id):
    try:
        return sb.table("portfolio_transactions").select("*").eq("user_id",user_id).order("transaction_date").execute().data or []
    except Exception as e:
        st.error(f"Portfolio पढ्न सकिएन: {e}"); return []

PAGES=["📊 MARKET DASHBOARD","🔍 STOCK SCANNER","🏢 SECTOR EXPLORER","📚 FUNDAMENTAL ANALYSIS","📈 TECHNICAL ANALYSIS","📰 NEWS INTELLIGENCE","🧠 SMART RECOMMENDATIONS","💼 WATCHLIST & PORTFOLIO"]
if 'page' not in st.session_state: st.session_state.page="Home"
if 'watch' not in st.session_state: st.session_state.watch=[]

df,indices,summary,tops,errors=load_market()

st.markdown('<div class="edge-header"><div class="edge-logo">NEPSE EDGE</div><div class="edge-subtitle">NEPAL STOCK MARKET INTELLIGENCE</div></div>',unsafe_allow_html=True)
with st.sidebar:
    st.title("NEPSE EDGE")
    if st.button("🏠 HOME",use_container_width=True): st.session_state.page="Home"
    for p in PAGES:
        if st.button(p,use_container_width=True): st.session_state.page=p
    st.caption("Public YONEPSE mirror • Not official NEPSE data")

# helpers
symbols=sorted(df.symbol.dropna().astype(str).unique().tolist()) if not df.empty and 'symbol' in df else []
def stock_picker(key="stock"):
    if not symbols: st.warning("Company list is currently unavailable."); return None
    return st.selectbox("कम्पनी / Symbol खोज्नुहोस्",symbols,key=key)
def selected_row(sym):
    if df.empty:return None
    x=df[df.symbol.astype(str)==str(sym)]
    return x.iloc[0] if not x.empty else None
def show_stock_overview(sym):
    r=selected_row(sym)
    if r is None: st.warning("यस कम्पनीको मूल्य डाटा उपलब्ध छैन।"); return
    name=r.get('companyName',r.get('name',sym)); st.subheader(f"{name} ({sym})")
    c1,c2,c3,c4=st.columns(4)
    c1.metric("LTP",fmt(r.get('ltp'))); c2.metric("Change",fmt(r.get('change')),f"{fmt(r.get('percent_change'))}%")
    c3.metric("Volume",fmt(r.get('volume'))); c4.metric("Turnover",fmt(r.get('turnover')))
    st.caption(f"Sector: {r.get('sectorName','Not available')} • Updated: {r.get('last_updated','Timestamp unavailable')}")

def get_summary(label):
    for x in summary if isinstance(summary,list) else []:
        d=str(x.get('detail','')).lower()
        if label.lower() in d:return x.get('value','—')
    return '—'

def make_score(row):
    # Conservative screening score. No unsupported historical/fundamental/news data is fabricated.
    score=0; reasons=[]; coverage=[]
    ch=row.get('percent_change',np.nan); vol=row.get('volume',np.nan); turnover=row.get('turnover',np.nan); ltp=row.get('ltp',np.nan); prev=row.get('previous_close',np.nan)
    if pd.notna(ch):
        coverage.append('दैनिक मूल्य परिवर्तन')
        if ch>0: score+=15; reasons.append('आजको मूल्य सकारात्मक')
        elif ch==0: score+=7
    if pd.notna(vol) and vol>0: score+=8; coverage.append('Volume')
    if pd.notna(turnover) and turnover>0: score+=7; coverage.append('Turnover')
    if pd.notna(ltp) and pd.notna(prev) and prev>0:
        if ltp>=prev: score+=5
        coverage.append('Previous close तुलना')
    # Remaining 65 points require verified history, financials and news, not available in this feed.
    return score,reasons,coverage

if st.session_state.page=="Home":
    st.markdown('<div class="section-heading">Explore NEPSE EDGE</div>',unsafe_allow_html=True)
    for i in range(0,8,2):
        a,b=st.columns(2,gap="small")
        with a:
            if st.button(PAGES[i],key=f"home{i}"): st.session_state.page=PAGES[i]
        with b:
            if st.button(PAGES[i+1],key=f"home{i+1}"): st.session_state.page=PAGES[i+1]
    st.markdown("### Market Snapshot")
    a,b=st.columns(2); a.metric("Total Turnover",get_summary("Total Turnover")); b.metric("Traded Shares",get_summary("Total Traded Shares"))
    a,b=st.columns(2); a.metric("Transactions",get_summary("Total Transactions")); b.metric("Scrips Traded",get_summary("Total Scrips Traded"))
    st.caption("डेटा सार्वजनिक YONEPSE mirror बाट आउँछ; बजार बन्दपछिको/ढिलो डाटा हुन सक्छ।")
    if errors: st.warning("केही data endpoint उपलब्ध भएनन्: "+"; ".join(errors))

elif st.session_state.page==PAGES[0]:
    st.title("📊 Market Dashboard")
    for x in indices if isinstance(indices,list) else []:
        if str(x.get('index','')).lower()=='nepse index':
            metric("NEPSE Index",fmt(x.get('currentValue',x.get('close'))),f"{fmt(x.get('perChange'))}%")
    a,b,c=st.columns(3); a.metric("Turnover",get_summary("Total Turnover")); b.metric("Shares",get_summary("Total Traded Shares")); c.metric("Transactions",get_summary("Total Transactions"))
    if indices: st.subheader("Market Indices"); st.dataframe(pd.DataFrame(indices),use_container_width=True,hide_index=True)
    if not df.empty:
        adv=int((df.get('change',pd.Series(dtype=float))>0).sum()); dec=int((df.get('change',pd.Series(dtype=float))<0).sum()); unchanged=int((df.get('change',pd.Series(dtype=float))==0).sum())
        st.subheader("Market Breadth"); a,b,c=st.columns(3); a.metric("Advancers",adv); b.metric("Decliners",dec); c.metric("Unchanged",unchanged)
        st.subheader("Top Movers")
        x=df.sort_values('percent_change',ascending=False) if 'percent_change' in df else df
        a,b=st.columns(2)
        with a: st.write("Top Gainers"); st.dataframe(x.head(10),use_container_width=True,hide_index=True)
        with b: st.write("Top Losers"); st.dataframe(x.tail(10).sort_values('percent_change'),use_container_width=True,hide_index=True)
    else: st.error("Market price feed उपलब्ध छैन।")

elif st.session_state.page==PAGES[1]:
    st.title("🔍 Stock Scanner")
    q=st.text_input("कम्पनीको नाम वा Symbol खोज्नुहोस्")
    view=df.copy()
    if q and not view.empty:
        view=view[view.astype(str).apply(lambda col:col.str.contains(q,case=False,na=False)).any(axis=1)]
    if not view.empty:
        cols=[c for c in ['symbol','companyName','sectorName','ltp','change','percent_change','volume','turnover'] if c in view]
        st.write(f"कुल {len(view)} कम्पनी"); st.dataframe(view[cols].sort_values('turnover',ascending=False) if 'turnover' in cols else view[cols],use_container_width=True,hide_index=True)
    else: st.info("खोजी नतिजा वा डाटा उपलब्ध छैन।")

elif st.session_state.page==PAGES[2]:
    st.title("🏢 Sector Explorer")
    if not df.empty and 'sectorName' in df:
        sectors=sorted(df.sectorName.dropna().astype(str).unique())
        sector=st.selectbox("Sector छान्नुहोस्",["All Sectors"]+sectors)
        v=df if sector=="All Sectors" else df[df.sectorName.astype(str)==sector]
        st.write(f"{sector}: {len(v)} कम्पनी")
        st.dataframe(v,use_container_width=True,hide_index=True)
    else: st.warning("Sector वर्गीकरण उपलब्ध छैन।")

elif st.session_state.page==PAGES[3]:
    st.title("📚 Fundamental Analysis")
    sym=stock_picker("fund_stock")
    if sym:
        show_stock_overview(sym)
        st.subheader("Fundamental Data")
        st.info("हाल जडान भएको सार्वजनिक feed मा EPS, P/E, Net Profit, Book Value, Debt र quarterly report को प्रमाणित विवरण छैन। यी मानहरू अनुमान गरेर देखाइएको छैन। कम्पनीको आधिकारिक quarterly report वा NEPSE disclosure उपलब्ध गराएपछि मात्र ratios गणना गर्न सकिन्छ।")
        st.write("Sector",(selected_row(sym).get('sectorName','—') if selected_row(sym) is not None else '—'))

elif st.session_state.page==PAGES[4]:
    st.title("📈 Technical Analysis")
    sym=stock_picker("technical_stock")
    if sym:
        show_stock_overview(sym)
        st.subheader("Price Chart")
        st.warning("हाल जोडिएको YONEPSE mirror मा verified daily OHLC historical candles उपलब्ध छैनन्। त्यसैले यहाँ नक्कली Candlestick, RSI वा MACD देखाइएको छैन।")
        st.info("यो feed बाट हालको LTP मात्र उपलब्ध हुँदा सही RSI/MACD/EMA का लागि कम्तीमा 14–26+ दिनको ऐतिहासिक मूल्य शृङ्खला आवश्यक हुन्छ। ऐतिहासिक स्रोत जडान भएपछि चार्ट र indicators स्वतः सक्रिय हुनेछन्।")
        r=selected_row(sym)
        if r is not None:
            st.subheader("Available Price Snapshot")
            st.dataframe(pd.DataFrame([r]),use_container_width=True,hide_index=True)

elif st.session_state.page==PAGES[5]:
    st.title("📰 News Intelligence")
    st.info("यस संस्करणमा सार्वजनिक market feed मात्र जडान छ। छुट्टै विश्वसनीय समाचार API/NEPSE notice feed जडान नभएकाले समाचार शीर्षक बनावटी रूपमा देखाइएको छैन।")
    sym=stock_picker("news_stock")
    if sym:
        st.subheader(f"{sym} — Company News")
        st.warning("यस कम्पनीका प्रमाणित समाचार तथा disclosures को feed अझै जडान भएको छैन।")
        st.caption("अर्को चरणमा स्रोत र प्रकाशित मितिसहित कम्पनीअनुसार समाचार जोडिनेछ।")

elif st.session_state.page==PAGES[6]:
    st.title("🧠 Smart Recommendations")
    st.caption("Conservative preliminary screen • यो व्यक्तिगत लगानी सल्लाह होइन।")
    n=st.select_slider("कति कम्पनी देखाउने?",options=[5,8,10,15,20,30],value=10)
    if not df.empty:
        scored=[]
        for _,r in df.iterrows():
            sc,why,cov=make_score(r); scored.append({"Symbol":r.get('symbol'),"Company":r.get('companyName',r.get('name','')),"Score / 100":sc,"Preliminary Signal":"WATCH — insufficient verified data","Reasons":", ".join(why) or "पर्याप्त सकारात्मक संकेत छैन","Available data":", ".join(cov)})
        rec=pd.DataFrame(scored).sort_values('Score / 100',ascending=False).head(n)
        st.dataframe(rec,use_container_width=True,hide_index=True)
        st.error("महत्त्वपूर्ण: अहिलेको feed मा ऐतिहासिक indicators, audited fundamentals र verified news समावेश छैनन्। त्यसैले कुनै कम्पनीलाई Strong Buy भनेर सिफारिस गरिएको छैन। हालका स्कोर पूर्ण 100-point recommendation होइनन्।")
        st.caption("अन्तिम recommendation engine का लागि historical OHLC, quarterly financials र dated company news जोडेर backtest गर्नुपर्छ।")
    else: st.warning("Market data उपलब्ध छैन।")

elif st.session_state.page==PAGES[7]:
    st.title("💼 Watchlist & Portfolio")
    st.subheader("Watchlist")
    sym=stock_picker("watch_stock")
    if sym and st.button("＋ Add to Watchlist"):
        if sym not in st.session_state.watch: st.session_state.watch.append(sym)
    if st.session_state.watch: st.write(", ".join(st.session_state.watch))
    st.divider(); st.subheader("Buy / Sell Portfolio")
    user_id=portfolio_login()
    if user_id:
        with st.form("transaction_form"):
            symbol=st.selectbox("Company",symbols if symbols else ["No data"])
            typ=st.selectbox("Transaction",["BUY","SELL"])
            qty=st.number_input("Quantity",min_value=1,step=1)
            price=st.number_input("Price per share (Rs.)",min_value=0.01,step=0.5)
            txdate=st.date_input("Transaction date",value=date.today())
            notes=st.text_input("Notes (optional)")
            submitted=st.form_submit_button("Save Transaction")
            if submitted:
                try:
                    current=get_transactions(user_id)
                    net=sum(int(t["quantity"]) if t["transaction_type"]=="BUY" else -int(t["quantity"]) for t in current if t["symbol"]==symbol)
                    if typ=="SELL" and qty>net: st.error(f"Sell quantity बढी भयो। हाल {net} कित्ता मात्र बाँकी छ।")
                    else:
                        sb.table("portfolio_transactions").insert({"user_id":user_id,"symbol":symbol,"transaction_type":typ,"quantity":int(qty),"price":float(price),"transaction_date":str(txdate),"notes":notes}).execute()
                        st.success("Transaction cloud database मा सुरक्षित भयो।"); st.rerun()
                except Exception as e: st.error(f"Save गर्न सकिएन: {e}")
        tx=get_transactions(user_id)
        if tx:
            tdf=pd.DataFrame(tx)
            st.subheader("Transaction History")
            st.dataframe(tdf,use_container_width=True,hide_index=True)
            st.subheader("Holdings")
            holdings=[]
            for s in sorted(tdf.symbol.unique()):
                part=tdf[tdf.symbol==s]
                buys=part[part.transaction_type=="BUY"]; sells=part[part.transaction_type=="SELL"]
                bought=int(buys.quantity.sum()); sold=int(sells.quantity.sum()); balance=bought-sold
                avg=float((buys.quantity*buys.price).sum()/bought) if bought else 0
                current=selected_row(s); ltp=float(current.get("ltp")) if current is not None and pd.notna(current.get("ltp")) else np.nan
                holdings.append({"Symbol":s,"Bought":bought,"Sold":sold,"Balance":balance,"Avg Buy Price":round(avg,2),"LTP":ltp,"Unrealized P/L":round((ltp-avg)*balance,2) if pd.notna(ltp) else None})
            st.dataframe(pd.DataFrame(holdings),use_container_width=True,hide_index=True)
        else: st.info("अहिलेसम्म कारोबार थपिएको छैन।")
    else:
        st.info("पहिले email OTP verify गरेपछि Buy/Sell रेकर्ड थप्न र सुरक्षित राख्न सक्नुहुन्छ।")

st.markdown('<div class="edge-footer">NEPSE EDGE © 2026<br/>INDEPENDENT STOCK MARKET INTELLIGENCE PLATFORM</div>',unsafe_allow_html=True)
