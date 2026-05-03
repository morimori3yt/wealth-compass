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

# --- カスタムCSS ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', 'Noto Sans JP', sans-serif; }
.main { background-color: #0e1117; }
.market-card { background: #1e2128; padding: 1rem; border-radius: 8px; border: 1px solid #30363d; margin-bottom: 0.5rem; }
.price-up { color: #00c805; font-weight: bold; }
.price-down { color: #ff3b30; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- セッション状態の初期化 ---
if 'fire_age_val' not in st.session_state: st.session_state.fire_age_val = 50

# --- データ取得関数 ---
@st.cache_data(ttl=3600)
def fetch_news(keyword):
    encoded_keyword = urllib.parse.quote(keyword)
    rss_url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=ja&gl=JP&ceid=JP:ja"
    try:
        feed = feedparser.parse(rss_url)
        return feed.entries
    except: return []

@st.cache_data(ttl=600)
def get_market_data(ticker_symbol, period="1mo"):
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period=period)
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=3600*24)
def get_earnings_calendar():
    # 主要銘柄の決算予定を簡易的に取得
    tickers = {
        "トヨタ": "7203.T", "ソニー": "6758.T", "ソフトバンクG": "9984.T",
        "Apple": "AAPL", "Microsoft": "MSFT", "Google": "GOOGL", 
        "Amazon": "AMZN", "NVIDIA": "NVDA", "Tesla": "TSLA"
    }
    events = []
    for name, symbol in tickers.items():
        try:
            t = yf.Ticker(symbol)
            cal = t.calendar
            if cal is not None and not cal.empty:
                # 辞書形式またはDataFrame形式で返る場合がある
                e_date = cal.iloc[0,0] if hasattr(cal, 'iloc') else cal.get('Earnings Date', [None])[0]
                if e_date:
                    events.append({
                        "日付": e_date.strftime('%Y-%m-%d'),
                        "国": "JP" if ".T" in symbol else "US",
                        "イベント": f"{name} ({symbol}) 決算発表"
                    })
        except: continue
    return events

# --- メインコンテンツ ---
st.title("🧭 資産形成の羅針盤 (Wealth Compass) Ver 2.0")

tabs = st.tabs(["📊 マーケット実況", "📅 カレンダー", "🚀 FIREシミュレーター", "🇺🇸 ニュース"])

# --- Tab 1: マーケット実況 ---
with tabs[0]:
    st.header("マーケット実況（日米主要指数）")
    indices = {
        "日経平均": "^N225", "TOPIX": "^TPX", "グロース250": "1552.T",
        "NYダウ": "^DJI", "S&P 500": "^GSPC", "ナスダック": "^IXIC",
        "ドル円": "JPY=X", "米国10年債": "^TNX", "ビットコイン": "BTC-USD"
    }
    
    cols = st.columns(3)
    for i, (name, symbol) in enumerate(indices.items()):
        with cols[i % 3]:
            df = get_market_data(symbol)
            if not df.empty:
                current_price = df['Close'].iloc[-1]
                prev_price = df['Close'].iloc[-2]
                diff = current_price - prev_price
                pct = (diff / prev_price) * 100
                color = "price-up" if diff >= 0 else "price-down"
                sign = "+" if diff >= 0 else ""
                
                st.markdown(f"""
                <div class="market-card">
                    <div style="font-size: 0.85rem; color: #8b949e;">{name}</div>
                    <div style="font-size: 1.4rem; font-weight: 700;">{current_price:,.2f}</div>
                    <div class="{color}" style="font-size: 0.9rem;">{sign}{diff:,.2f} ({sign}{pct:.2f}%)</div>
                </div>
                """, unsafe_allow_html=True)
                
                fig = px.line(df, x=df.index, y='Close', template="plotly_dark", height=120)
                fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), xaxis_visible=False, yaxis_visible=False, showlegend=False)
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# --- Tab 2: カレンダー ---
with tabs[1]:
    st.header("経済・決算カレンダー")
    col_c1, col_c2 = st.columns(2)
    with col_c1: show_jp = st.checkbox("日本を表示", value=True)
    with col_c2: show_us = st.checkbox("米国を表示", value=True)
    
    # 経済イベント（静的）
    static_events = [
        {"日付": "2024-05-15", "国": "US", "イベント": "米消費者物価指数 (CPI) 発表"},
        {"日付": "2024-05-22", "国": "US", "イベント": "FOMC議事録要旨公開"},
        {"日付": "2024-06-07", "国": "US", "イベント": "米雇用統計発表"},
        {"日付": "2024-05-25", "国": "JP", "イベント": "日本 消費者物価指数 (CPI)"},
        {"日付": "2024-06-14", "国": "JP", "イベント": "日銀金融政策決定会合 結果発表"},
    ]
    
    # 決算イベント（動的取得）
    with st.spinner("主要企業の決算予定を取得中..."):
        dynamic_events = get_earnings_calendar()
    
    all_events = static_events + dynamic_events
    df_ev = pd.DataFrame(all_events).sort_values("日付")
    
    # フィルタリング
    mask = pd.Series([False] * len(df_ev))
    if show_jp: mask |= (df_ev['国'] == 'JP')
    if show_us: mask |= (df_ev['国'] == 'US')
    
    display_df = df_ev[mask]
    if not display_df.empty:
        st.table(display_df.reset_index(drop=True))
    else:
        st.info("表示する予定がありません。")

# --- Tab 3: FIREシミュレーター ---
with tabs[2]:
    st.header("FIRE Simulator Pro")
    c_in, c_chart = st.columns([1, 2])
    
    with c_in:
        st.subheader("条件設定")
        age = st.number_input("現在の年齢", 18, 80, 30)
        reg_assets = st.number_input("特定口座 (万円)", 0.00, 100000.00, 400.00)
        nisa_assets = st.number_input("NISA口座 (万円)", 0.00, 100000.00, 100.00)
        monthly_inv = st.number_input("毎月の積立額 (万円)", 0.00, 100.00, 10.00)
        
        st.markdown("**通常(Base)利回り (%)**")
        ret_pre = st.number_input("積立期", 0.0, 20.0, 5.0)
        ret_post = st.number_input("リタイア後", 0.0, 20.0, 3.0)
        
        with st.expander("強気・弱気シナリオの利回り調整"):
            bull_diff = st.slider("強気シナリオの上乗せ利回り", 0.0, 5.0, 2.0)
            bear_diff = st.slider("弱気シナリオの下振れ利回り", 0.0, 5.0, 2.0)
        
        fire_age = st.number_input("リタイア希望年齢", 18, 100, st.session_state.fire_age_val)
        retirement_allowance = st.number_input("想定退職金 (万円)", 0.00, 10000.00, 0.00)
        living_exp = st.number_input("生活費 (月額/万円)", 0.0, 200.0, 25.0)
        pension_val = st.number_input("受給年金 (月額/万円)", 0.0, 50.0, 15.0)
        inf_rate = st.number_input("インフレ率 (%)", 0.0, 10.0, 1.0)
        
        show_scenarios = st.multiselect("表示するライン", ["通常", "強気", "弱気"], default=["通常", "強気", "弱気"])

    with c_chart:
        simulator = FIRESimulator()
        all_res = simulator.calculate({
            'currentAge': age, 'currentAssets': reg_assets + nisa_assets, 'nisaAssets': nisa_assets,
            'monthlyInvestment': monthly_inv, 'expectedReturnPre': ret_pre, 'expectedReturnPost': ret_post,
            'expectedReturnPreBull': ret_pre + bull_diff, 'expectedReturnPostBull': ret_post + bull_diff,
            'expectedReturnPreBear': max(0, ret_pre - bear_diff), 'expectedReturnPostBear': max(0, ret_post - bear_diff),
            'fireAge': fire_age, 'livingExpense': living_exp, 'inflationRate': inf_rate,
            'pensionAmount': pension_val, 'retirementAllowance': retirement_allowance
        })
        
        fig = go.Figure()
        colors = {"通常": "#1f6feb", "強気": "#00c805", "弱気": "#ff3b30"}
        for name in show_scenarios:
            res = all_res[name]
            df_h = pd.DataFrame(res['history'])
            fig.add_trace(go.Scatter(x=df_h['age'], y=df_h['totalAssets'], name=name, line=dict(color=colors[name], width=3)))
        
        fig.update_layout(title="将来資産の3シナリオ推移", xaxis_title="年齢", yaxis_title="資産額 (万円)", template="plotly_dark", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
        
        # 診断結果の並列表示
        st.subheader("診断レポート")
        r_cols = st.columns(len(show_scenarios) if show_scenarios else 1)
        for idx, name in enumerate(show_scenarios):
            res = all_res[name]
            with r_cols[idx]:
                st.info(f"**{name}**")
                if res['exhaustionAge']: st.error(f"枯渇: {res['exhaustionAge']}歳")
                else: st.success("100歳超え")
                st.metric("最終資産", f"{res['finalAssets']:,.0f}万円")

        # JPEG保存
        if st.button("🖼 結果を画像(JPEG)で保存する"):
            img_bytes = fig.to_image(format="jpg", width=1200, height=700)
            st.download_button(label="画像をダウンロード", data=img_bytes, file_name=f"WealthCompass_{datetime.datetime.now().strftime('%Y%m%d')}.jpg", mime="image/jpeg")

# --- Tab 4: ニュース ---
with tabs[3]:
    st.header("最新ニュース")
    news_kw = st.selectbox("カテゴリ", ["米国株 経済", "日本株 市場", "ビットコイン 暗号資産"])
    news_list = fetch_news(news_kw)
    for n in news_list[:12]:
        st.markdown(f'<div style="background: #1e2128; padding: 1rem; border-radius: 8px; margin-bottom: 0.8rem; border-left: 4px solid #1f6feb;"><b>{n.title}</b><br><small>{n.published}</small><br><a href="{n.link}" target="_blank">詳細</a></div>', unsafe_allow_html=True)
