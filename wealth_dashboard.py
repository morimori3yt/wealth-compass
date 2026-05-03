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
    page_title="資産形成の羅針盤",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- プロフェッショナル・プレミアム・デザイン (CSS) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Noto+Sans+JP:wght@400;500;700&display=swap');

:root {
    --bg-color: #0b0e14;
    --card-bg: #161b22;
    --border-color: #30363d;
    --text-primary: #ffffff;
    --text-secondary: #8b949e;
    --accent-blue: #58a6ff;
    --price-up: #39d353;
    --price-down: #ff4d4d;
}

html, body, [class*="css"] {
    font-family: 'Inter', 'Noto Sans JP', sans-serif;
    background-color: var(--bg-color);
    color: var(--text-primary);
}

/* カード共通 */
.premium-card {
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 1rem;
    box-shadow: 0 4px 20px rgba(0,0,0,0.2);
}

/* マーケットカード */
.m-card {
    text-align: left;
    min-height: 140px;
}
.m-label { font-size: 0.85rem; color: var(--text-secondary); font-weight: 500; margin-bottom: 0.5rem; }
.m-price-val { font-size: 1.6rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.25rem; }
.m-change-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: 600;
}
.bg-up { background: rgba(57, 211, 83, 0.15); color: var(--price-up); }
.bg-down { background: rgba(255, 77, 77, 0.15); color: var(--price-down); }

/* ニュースセクション */
.n-title { font-size: 1.1rem; font-weight: 700; color: #ffffff !important; line-height: 1.4; margin-bottom: 0.5rem; text-decoration: none; }
.n-meta { font-size: 0.8rem; color: var(--text-secondary); display: flex; align-items: center; gap: 10px; }
.n-tag { background: #21262d; padding: 2px 8px; border-radius: 100px; color: var(--accent-blue); font-size: 0.7rem; font-weight: 600; }

/* FIREレポート */
.report-card {
    background: linear-gradient(135deg, #1c2128 0%, #161b22 100%);
    border-left: 4px solid var(--accent-blue);
    padding: 1rem;
    border-radius: 0 8px 8px 0;
}
</style>
""", unsafe_allow_html=True)

# --- セッション管理 ---
if 'fire_age_val' not in st.session_state: st.session_state.fire_age_val = 50

# --- データ関数 ---
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
    tickers = {"トヨタ": "7203.T", "ソニー": "6758.T", "ソフトバンクG": "9984.T", "三菱UFJ": "8306.T", "Apple": "AAPL", "Microsoft": "MSFT", "NVIDIA": "NVDA"}
    events = []
    for name, symbol in tickers.items():
        try:
            t = yf.Ticker(symbol)
            cal = t.calendar
            if cal is not None and not cal.empty:
                e_date = cal.iloc[0,0] if hasattr(cal, 'iloc') else cal.get('Earnings Date', [None])[0]
                if e_date:
                    events.append({
                        "日時(JST)": e_date.strftime('%Y-%m-%d') + (" 15:00" if ".T" in symbol else " 08:00"),
                        "国": "JP" if ".T" in symbol else "US", "イベント": f"{name} 決算発表"
                    })
        except: continue
    return events

# --- 広告 ---
def display_ad():
    st.markdown("""
    <div style="text-align:center; margin: 1.5rem 0;">
        <a href="https://rpx.a8.net/svt/ejp?a8mat=4B3GYD+C0U5KI+2HOM+69P01&rakuten=y&a8ejpredirect=http%3A%2F%2Fhb.afl.rakuten.co.jp%2Fhgc%2F0ea62065.34400275.0ea62066.204f04c0%2Fa26050208529_4B3GYD_C0U5KI_2HOM_69P01%3Fpc%3Dhttp%253A%252F%252Fwww.rakuten.co.jp%252F%26m%3Dhttp%253A%252F%252Fm.rakuten.co.jp%252F" rel="nofollow">
        <img src="https://hbb.afl.rakuten.co.jp/hsb/0eb4bbc7.e9e6f789.0eb4bbaa.95151395/" border="0" style="border-radius: 8px;"></a>
    </div>
    """, unsafe_allow_html=True)

# --- 構成 ---
st.title("🧭 資産形成の羅針盤")
display_ad()

tabs = st.tabs(["📊 マーケット状況", "📰 ニュース", "📅 カレンダー", "🚀 FIREシミュレーター"])

# --- Tab 1: マーケット状況 ---
with tabs[0]:
    indices = {"日経平均": "^N225", "TOPIX": "^TPX", "グロース250": "1552.T", "NYダウ": "^DJI", "S&P 500": "^GSPC", "ナスダック": "^IXIC", "ドル円": "JPY=X", "米国10年債": "^TNX", "ビットコイン": "BTC-USD"}
    selected = st.multiselect("表示する指標を選択", list(indices.keys()), default=list(indices.keys())[:6])
    
    m_cols = st.columns(3)
    for idx, name in enumerate(selected):
        symbol = indices[name]
        with m_cols[idx % 3]:
            df = get_market_data(symbol)
            if not df.empty:
                curr = df['Close'].iloc[-1]
                diff = curr - df['Close'].iloc[-2]
                pct = (diff / df['Close'].iloc[-2]) * 100
                cls = "bg-up" if diff >= 0 else "bg-down"
                sign = "+" if diff >= 0 else ""
                
                st.markdown(f"""
                <div class="premium-card m-card">
                    <div class="m-label">{name}</div>
                    <div class="m-price-val">{curr:,.2f}</div>
                    <div class="m-change-badge {cls}">{sign}{diff:,.2f} ({sign}{pct:.2f}%)</div>
                </div>
                """, unsafe_allow_html=True)
                
                fig = px.area(df, x=df.index, y='Close', template="plotly_dark", height=80)
                fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), xaxis_visible=False, yaxis_visible=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                fig.update_traces(line_color='#58a6ff', fillcolor='rgba(88, 166, 255, 0.1)')
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# --- Tab 2: ニュース ---
with tabs[1]:
    n_col1, n_col2 = st.columns(2)
    with n_col1:
        st.subheader("🇯🇵 日本経済")
        news_jp = fetch_news("日本株 経済")
        for n in news_jp[:10]:
            st.markdown(f"""
            <div class="premium-card">
                <a href="{n.link}" target="_blank" class="n-title">{n.title}</a>
                <div class="n-meta"><span class="n-tag">JP</span> {n.published}</div>
            </div>
            """, unsafe_allow_html=True)
    with n_col2:
        st.subheader("🇺🇸 米国経済")
        news_us = fetch_news("米国株 FRB")
        for n in news_us[:10]:
            st.markdown(f"""
            <div class="premium-card">
                <a href="{n.link}" target="_blank" class="n-title">{n.title}</a>
                <div class="n-meta"><span class="n-tag">US</span> {n.published}</div>
            </div>
            """, unsafe_allow_html=True)

# --- Tab 3: カレンダー ---
with tabs[2]:
    st.subheader("JST カレンダー")
    c_f1, c_f2 = st.columns(2)
    with c_f1: show_jp_c = st.checkbox("🇯🇵 日本を表示", value=True)
    with c_f2: show_us_c = st.checkbox("🇺🇸 米国を表示", value=True)
    
    with st.spinner("更新中..."):
        df_cal = pd.DataFrame([
            {"日時(JST)": "2024-05-15 21:30", "国": "US", "イベント": "米CPI発表"},
            {"日時(JST)": "2024-05-24 08:30", "国": "JP", "イベント": "日本CPI発表"},
            {"日時(JST)": "2024-06-07 21:30", "国": "US", "イベント": "米雇用統計"}
        ] + get_earnings_calendar()).sort_values("日時(JST)")
    
    mask = pd.Series([False] * len(df_cal))
    if show_jp_c: mask |= (df_cal['国'] == 'JP')
    if show_us_c: mask |= (df_cal['国'] == 'US')
    st.dataframe(df_cal[mask], use_container_width=True)

# --- Tab 4: FIREシミュレーター ---
with tabs[3]:
    f_in, f_out = st.columns([1, 2])
    with f_in:
        st.subheader("資産形成シミュレーション")
        curr_age = st.number_input("現在の年齢", 18, 80, 30)
        total_assets = st.number_input("現在の資産合計 (万円)", 0.0, 100000.0, 500.0, step=0.1)
        nisa_assets = st.number_input("うちNISA資産 (万円)", 0.0, 100000.0, 100.0, step=0.1)
        m_inv = st.number_input("毎月の積立額 (万円)", 0.0, 100.0, 10.0, step=0.1)
        
        st.markdown("**利回り設定 (%)**")
        r_pre = st.number_input("通常利回り - 積立期", 0.0, 20.0, 5.0, step=0.1)
        r_post = st.number_input("通常利回り - FIRE後", 0.0, 20.0, 3.0, step=0.1)
        r_bull = st.number_input("強気時 上乗せ分", 0.0, 10.0, 2.0, step=0.1)
        r_bear = st.number_input("弱気時 下振れ分", 0.0, 10.0, 2.0, step=0.1)
        
        f_age = st.number_input("FIRE年齢", 18, 100, st.session_state.fire_age_val)
        ret_al = st.number_input("想定退職金 (万円)", 0.0, 10000.0, 0.0, step=0.1)
        p_age = st.number_input("年金開始年齢", 60, 75, 65)
        p_val = st.number_input("年金月額 (万円)", 0.0, 50.0, 15.0, step=0.1)
        l_exp = st.number_input("FIRE後生活費 (月額/万円)", 0.0, 200.0, 25.0, step=0.1)
        inf = st.number_input("想定インフレ率 (%)", 0.0, 10.0, 1.0, step=0.1)
        
        show_scen = st.multiselect("シナリオ表示", ["通常", "強気", "弱気"], default=["通常", "強気", "弱気"])

    with f_out:
        sim = FIRESimulator()
        all_res = sim.calculate({
            'currentAge': curr_age, 'currentAssets': total_assets, 'nisaAssets': nisa_assets,
            'monthlyInvestment': m_inv, 'expectedReturnPre': r_pre, 'expectedReturnPost': r_post,
            'expectedReturnPreBull': r_pre + r_bull, 'expectedReturnPostBull': r_post + r_bull,
            'expectedReturnPreBear': max(0, r_pre - r_bear), 'expectedReturnPostBear': max(0, r_post - r_bear),
            'fireAge': f_age, 'livingExpense': l_exp, 'inflationRate': inf,
            'pensionAmount': p_val, 'pensionAge': p_age, 'retirementAllowance': ret_al
        })
        
        fig = go.Figure()
        clrs = {"通常": "#58a6ff", "強気": "#39d353", "弱気": "#ff4d4d"}
        for n in show_scen:
            df_h = pd.DataFrame(all_res[n]['history'])
            fig.add_trace(go.Scatter(x=df_h['age'], y=df_h['totalAssets'], name=n, line=dict(color=clrs[n], width=3)))
        
        fig.update_layout(title="資産推移シミュレーション", xaxis_title="年齢", yaxis_title="資産額 (万円)", template="plotly_dark", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
        
        # 診断レポート（復活）
        st.subheader("📋 シミュレーション診断レポート")
        rep_cols = st.columns(3)
        for idx, n in enumerate(show_scen):
            r = all_res[n]
            with rep_cols[idx]:
                st.markdown(f"""
                <div class="report-card">
                    <div style="font-weight:700; color:{clrs[n]};">{n}シナリオ</div>
                    <div style="font-size:0.85rem; margin-top:5px;">
                        {'✅ 100歳まで安泰' if not r['exhaustionAge'] else f'⚠️ {r["exhaustionAge"]}歳で資産枯渇'}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.metric("100歳時の資産額", f"{r['finalAssets']:,.0f}万円")

        if st.button("🖼 結果をJPEG画像で保存"):
            buf = io.BytesIO()
            fig.write_image(buf, format="jpg", width=1200, height=800)
            st.download_button(label="画像をダウンロード", data=buf.getvalue(), file_name="wealth_compass_report.jpg", mime="image/jpeg")
