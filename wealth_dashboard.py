import streamlit as st
import feedparser
import urllib.parse
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
from simulation_logic import FIRESimulator
import datetime
import io

# --- ページ設定 ---
st.set_page_config(
    page_title="資産形成の羅針盤 | マーケット実況 & FIRE",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- カスタムCSS (世界の株価風) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', 'Noto Sans JP', sans-serif; background-color: #000000; }

/* 世界の株価風カード */
.market-box {
    background: #111111;
    border: 1px solid #222222;
    padding: 10px;
    border-radius: 4px;
    text-align: center;
    margin-bottom: 10px;
}
.m-title { font-size: 0.8rem; color: #aaaaaa; margin-bottom: 5px; }
.m-price { font-size: 1.2rem; font-weight: 700; color: #ffffff; }
.m-up { color: #00ff00; font-size: 0.85rem; }
.m-down { color: #ff3333; font-size: 0.85rem; }

/* ニュースカード */
.news-entry {
    border-bottom: 1px solid #222222;
    padding: 10px 0;
}
.news-t { font-weight: 600; font-size: 0.95rem; color: #eeeeee; }
.news-m { font-size: 0.75rem; color: #888888; }
</style>
""", unsafe_allow_html=True)

# --- セッション状態 ---
if 'fire_age_val' not in st.session_state: st.session_state.fire_age_val = 50

# --- データ取得 ---
@st.cache_data(ttl=1800)
def fetch_news(keyword):
    encoded = urllib.parse.quote(keyword)
    rss_url = f"https://news.google.com/rss/search?q={encoded}&hl=ja&gl=JP&ceid=JP:ja"
    try:
        feed = feedparser.parse(rss_url)
        return feed.entries
    except: return []

@st.cache_data(ttl=600)
def get_market_data(ticker_symbol, period="5d"):
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period=period)
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=3600*12)
def get_earnings_calendar():
    tickers = {
        "トヨタ": "7203.T", "ソニー": "6758.T", "ソフトバンクG": "9984.T", "三菱UFJ": "8306.T",
        "Apple": "AAPL", "Microsoft": "MSFT", "Google": "GOOGL", "Amazon": "AMZN", "NVIDIA": "NVDA"
    }
    events = []
    for name, symbol in tickers.items():
        try:
            t = yf.Ticker(symbol)
            cal = t.calendar
            if cal is not None and not cal.empty:
                e_date = cal.iloc[0,0] if hasattr(cal, 'iloc') else cal.get('Earnings Date', [None])[0]
                if e_date:
                    # 日本時間考慮（米国銘柄は夜間・翌朝）
                    time_str = "08:00 (JST)" if "AAPL" in symbol or "NVDA" in symbol else "15:00 (JST)"
                    events.append({
                        "日時(JST)": e_date.strftime('%Y-%m-%d') + " " + time_str,
                        "国": "JP" if ".T" in symbol else "US",
                        "イベント": f"{name} 決算発表"
                    })
        except: continue
    return events

# --- 広告表示 ---
def display_ad():
    st.markdown("""
    <a href="https://rpx.a8.net/svt/ejp?a8mat=4B3GYD+C0U5KI+2HOM+69P01&rakuten=y&a8ejpredirect=http%3A%2F%2Fhb.afl.rakuten.co.jp%2Fhgc%2F0ea62065.34400275.0ea62066.204f04c0%2Fa26050208529_4B3GYD_C0U5KI_2HOM_69P01%3Fpc%3Dhttp%253A%252F%252Fwww.rakuten.co.jp%252F%26m%3Dhttp%253A%252F%252Fm.rakuten.co.jp%252F" rel="nofollow">
    <img src="https://hbb.afl.rakuten.co.jp/hsb/0eb4bbc7.e9e6f789.0eb4bbaa.95151395/" border="0"></a>
    <img border="0" width="1" height="1" src="https://www12.a8.net/0.gif?a8mat=4B3GYD+C0U5KI+2HOM+69P01" alt="">
    """, unsafe_allow_html=True)

# --- メインコンテンツ ---
st.title("🧭 資産形成の羅針盤")

tabs = st.tabs(["📊 マーケット状況", "📰 ニュース", "📅 カレンダー", "🚀 FIREシミュレーター"])

# --- Tab 1: マーケット状況 (世界の株価風) ---
with tabs[0]:
    all_indices = {
        "日経平均": "^N225", "TOPIX": "^TPX", "グロース250": "1552.T",
        "NYダウ": "^DJI", "S&P 500": "^GSPC", "ナスダック": "^IXIC",
        "ドル円": "JPY=X", "米国10年債": "^TNX", "ビットコイン": "BTC-USD"
    }
    selected = st.multiselect("表示対象を選択", list(all_indices.keys()), default=list(all_indices.keys())[:6])
    
    display_ad()
    
    m_cols = st.columns(3)
    for idx, name in enumerate(selected):
        symbol = all_indices[name]
        with m_cols[idx % 3]:
            df = get_market_data(symbol)
            if not df.empty:
                current = df['Close'].iloc[-1]
                diff = current - df['Close'].iloc[-2]
                pct = (diff / df['Close'].iloc[-2]) * 100
                cls = "m-up" if diff >= 0 else "m-down"
                sign = "+" if diff >= 0 else ""
                
                st.markdown(f"""
                <div class="market-box">
                    <div class="m-title">{name}</div>
                    <div class="m-price">{current:,.2f}</div>
                    <div class="{cls}">{sign}{diff:,.2f} ({sign}{pct:.2f}%)</div>
                </div>
                """, unsafe_allow_html=True)
                
                fig = go.Figure(data=go.Scatter(x=df.index, y=df['Close'], line=dict(color='#00ff00' if diff >= 0 else '#ff3333', width=2)))
                fig.update_layout(height=80, margin=dict(l=0, r=0, t=0, b=0), xaxis_visible=False, yaxis_visible=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# --- Tab 2: ニュース ---
with tabs[1]:
    st.header("マーケットニュース")
    display_ad()
    
    n_col1, n_col2 = st.columns(2)
    with n_col1:
        st.subheader("🇯🇵 日本株・経済")
        news_jp = fetch_news("日本株 経済 日本経済新聞")
        for n in news_jp[:8]:
            st.markdown(f'<div class="news-entry"><div class="news-t">{n.title}</div><div class="news-m">{n.published} | <a href="{n.link}" target="_blank">詳細</a></div></div>', unsafe_allow_html=True)
            
    with n_col2:
        st.subheader("🇺🇸 米国株・経済")
        news_us = fetch_news("米国株 ニューヨーク市場 FRB")
        for n in news_us[:8]:
            st.markdown(f'<div class="news-entry"><div class="news-t">{n.title}</div><div class="news-m">{n.published} | <a href="{n.link}" target="_blank">詳細</a></div></div>', unsafe_allow_html=True)

# --- Tab 3: カレンダー ---
with tabs[2]:
    st.header("JST 経済・決算カレンダー")
    display_ad()
    
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1: show_jp_c = st.checkbox("🇯🇵 日本を表示", value=True, key="c_jp")
    with filter_col2: show_us_c = st.checkbox("🇺🇸 米国を表示", value=True, key="c_us")
    
    # 経済イベント（日本時間想定）
    static_events = [
        {"日時(JST)": "2024-05-15 21:30", "国": "US", "イベント": "米消費者物価指数 (CPI)"},
        {"日時(JST)": "2024-05-23 03:00", "国": "US", "イベント": "FOMC議事録要旨"},
        {"日時(JST)": "2024-05-24 08:30", "国": "JP", "イベント": "日本 消費者物価指数 (CPI)"},
        {"日時(JST)": "2024-06-07 21:30", "国": "US", "イベント": "米雇用統計"},
        {"日時(JST)": "2024-06-14 12:30", "国": "JP", "イベント": "日銀政策金利決定会合"},
    ]
    
    with st.spinner("決算カレンダー更新中..."):
        dynamic_events = get_earnings_calendar()
    
    df_cal = pd.DataFrame(static_events + dynamic_events).sort_values("日時(JST)")
    mask = pd.Series([False] * len(df_cal))
    if show_jp_c: mask |= (df_cal['国'] == 'JP')
    if show_us_c: mask |= (df_cal['国'] == 'US')
    
    st.dataframe(df_cal[mask].reset_index(drop=True), use_container_width=True)

# --- Tab 4: FIREシミュレーター ---
with tabs[3]:
    st.header("FIRE Simulator Pro")
    display_ad()
    
    f_col1, f_col2 = st.columns([1, 2])
    with f_col1:
        st.subheader("条件設定")
        age = st.number_input("現在の年齢", 18, 80, 30)
        reg_assets = st.number_input("特定口座 (万円)", 0.00, 100000.00, 400.00, step=0.01)
        nisa_assets = st.number_input("NISA口座 (万円)", 0.00, 100000.00, 100.00, step=0.01)
        monthly_inv = st.number_input("毎月の積立額 (万円)", 0.00, 100.00, 10.00, step=0.01)
        
        st.markdown("**期待利回り (%)**")
        ret_pre = st.number_input("積立期 (通常)", 0.0, 30.0, 5.0, step=0.1)
        ret_post = st.number_input("リタイア後 (通常)", 0.0, 30.0, 3.0, step=0.1)
        
        ret_bull = st.number_input("強気シナリオの上乗せ利回り (%)", 0.0, 10.0, 2.0, step=0.1)
        ret_bear = st.number_input("弱気シナリオの下振れ利回り (%)", 0.0, 10.0, 2.0, step=0.1)
        
        fire_age = st.number_input("リタイア希望年齢", 18, 100, st.session_state.fire_age_val)
        retirement_allowance = st.number_input("想定退職金 (万円)", 0.0, 10000.0, 0.0, step=0.01)
        
        p_age = st.number_input("年金受給開始年齢", 60, 75, 65)
        p_val = st.number_input("受給年金額 (月額/万円)", 0.0, 50.0, 15.0, step=0.01)
        
        l_exp = st.number_input("生活費 (月額/万円)", 0.0, 200.0, 25.0, step=0.01)
        inf_rate = st.number_input("想定インフレ率 (%)", 0.0, 10.0, 1.0, step=0.1)
        
        scenarios_to_show = st.multiselect("表示するシナリオ", ["通常", "強気", "弱気"], default=["通常", "強気", "弱気"])

    with f_col2:
        sim = FIRESimulator()
        all_res = sim.calculate({
            'currentAge': age, 'currentAssets': reg_assets + nisa_assets, 'nisaAssets': nisa_assets,
            'monthlyInvestment': monthly_inv, 'expectedReturnPre': ret_pre, 'expectedReturnPost': ret_post,
            'expectedReturnPreBull': ret_pre + ret_bull, 'expectedReturnPostBull': ret_post + ret_bull,
            'expectedReturnPreBear': max(0, ret_pre - ret_bear), 'expectedReturnPostBear': max(0, ret_post - ret_bear),
            'fireAge': fire_age, 'livingExpense': l_exp, 'inflationRate': inf_rate,
            'pensionAmount': p_val, 'pensionAge': p_age, 'retirementAllowance': retirement_allowance
        })
        
        fig_f = go.Figure()
        clrs = {"通常": "#1f6feb", "強気": "#00ff00", "弱気": "#ff3333"}
        for name in scenarios_to_show:
            r = all_res[name]
            df_h = pd.DataFrame(r['history'])
            fig_f.add_trace(go.Scatter(x=df_h['age'], y=df_h['totalAssets'], name=name, line=dict(color=clrs[name], width=3)))
            
        fig_f.update_layout(title="将来資産推移", xaxis_title="年齢", yaxis_title="資産 (万円)", template="plotly_dark")
        st.plotly_chart(fig_f, use_container_width=True)
        
        if st.button("🖼 結果を画像(JPEG)で保存"):
            buf = io.BytesIO()
            fig_f.write_image(buf, format="jpg", width=1200, height=800)
            st.download_button(label="画像をダウンロード", data=buf.getvalue(), file_name="fire_result.jpg", mime="image/jpeg")
