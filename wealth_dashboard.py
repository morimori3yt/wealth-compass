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

# --- 世界の株価 UI 再現 (CSS) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans JP', sans-serif;
    background-color: #000000;
}

/* タイル形式のボックス */
.sk-box {
    padding: 12px 5px;
    border-radius: 2px;
    text-align: center;
    margin-bottom: 5px;
    color: #ffffff;
    border: 1px solid #333333;
}
.sk-up { background-color: #008000; } /* 上昇: 緑 */
.sk-down { background-color: #cc0000; } /* 下落: 赤 */

.sk-title { font-size: 0.75rem; font-weight: 700; margin-bottom: 2px; text-shadow: 1px 1px 2px rgba(0,0,0,0.5); }
.sk-price { font-size: 1.3rem; font-weight: 700; margin-bottom: 0px; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); }
.sk-change { font-size: 0.8rem; font-weight: 700; text-shadow: 1px 1px 2px rgba(0,0,0,0.5); }

/* ニュースの見出し */
.n-title { font-size: 1.05rem; font-weight: 700; color: #ffffff !important; line-height: 1.4; text-decoration: none; display: block; margin-bottom: 4px; }
.n-meta { font-size: 0.75rem; color: #aaaaaa; margin-bottom: 12px; border-bottom: 1px solid #222222; padding-bottom: 8px; }

/* 診断レポート */
.report-panel {
    background: #111111;
    border: 1px solid #333333;
    padding: 10px;
    border-radius: 4px;
    margin-top: 10px;
}
</style>
""", unsafe_allow_html=True)

# --- セッション管理 ---
if 'fire_age_val' not in st.session_state: st.session_state.fire_age_val = 50

# --- データ取得 ---
@st.cache_data(ttl=600)
def get_market_data(ticker_symbol, period="5d"):
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period=period)
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=1800)
def fetch_news(keyword):
    encoded = urllib.parse.quote(keyword)
    rss_url = f"https://news.google.com/rss/search?q={encoded}&hl=ja&gl=JP&ceid=JP:ja"
    try:
        feed = feedparser.parse(rss_url)
        return feed.entries
    except: return []

@st.cache_data(ttl=3600*12)
def get_earnings_calendar():
    tickers = {"トヨタ": "7203.T", "ソニー": "6758.T", "ソフトバンクG": "9984.T", "Apple": "AAPL", "Microsoft": "MSFT", "NVIDIA": "NVDA"}
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
    <div style="text-align:center; margin: 10px 0;">
        <a href="https://rpx.a8.net/svt/ejp?a8mat=4B3GYD+C0U5KI+2HOM+69P01&rakuten=y&a8ejpredirect=http%3A%2F%2Fhb.afl.rakuten.co.jp%2Fhgc%2F0ea62065.34400275.0ea62066.204f04c0%2Fa26050208529_4B3GYD_C0U5KI_2HOM_69P01%3Fpc%3Dhttp%253A%252F%252Fwww.rakuten.co.jp%252F%26m%3Dhttp%253A%252F%252Fm.rakuten.co.jp%252F" rel="nofollow">
        <img src="https://hbb.afl.rakuten.co.jp/hsb/0eb4bbc7.e9e6f789.0eb4bbaa.95151395/" border="0"></a>
    </div>
    """, unsafe_allow_html=True)

# --- 構成 ---
st.title("🧭 資産形成の羅針盤")
display_ad()

tabs = st.tabs(["📊 マーケット状況", "📰 ニュース", "📅 カレンダー", "🚀 FIREシミュレーター"])

# --- Tab 1: マーケット状況 (世界の株価再現) ---
with tabs[0]:
    indices = {"日経平均": "^N225", "TOPIX": "^TPX", "グロース250": "1552.T", "NYダウ": "^DJI", "S&P 500": "^GSPC", "ナスダック": "^IXIC", "ドル円": "JPY=X", "米国10年債": "^TNX", "ビットコイン": "BTC-USD"}
    selected = st.multiselect("表示対象", list(indices.keys()), default=list(indices.keys())[:6])
    
    m_cols = st.columns(4) # より高密度に
    for idx, name in enumerate(selected):
        symbol = indices[name]
        with m_cols[idx % 4]:
            df = get_market_data(symbol)
            if not df.empty:
                curr = df['Close'].iloc[-1]
                diff = curr - df['Close'].iloc[-2]
                pct = (diff / df['Close'].iloc[-2]) * 100
                bg_cls = "sk-up" if diff >= 0 else "sk-down"
                sign = "+" if diff >= 0 else ""
                
                st.markdown(f"""
                <div class="sk-box {bg_cls}">
                    <div class="sk-title">{name}</div>
                    <div class="sk-price">{curr:,.2f}</div>
                    <div class="sk-change">{sign}{diff:,.2f} ({sign}{pct:.2f}%)</div>
                </div>
                """, unsafe_allow_html=True)
                
                # ミニチャート (世界の株価風のシンプルなライン)
                fig = go.Figure(data=go.Scatter(x=df.index, y=df['Close'], line=dict(color='#ffffff', width=1.5)))
                fig.update_layout(height=50, margin=dict(l=0, r=0, t=0, b=0), xaxis_visible=False, yaxis_visible=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# --- Tab 2: ニュース ---
with tabs[1]:
    n_col1, n_col2 = st.columns(2)
    with n_col1:
        st.subheader("🇯🇵 日本経済")
        news_jp = fetch_news("日本株 経済")
        for n in news_jp[:10]:
            st.markdown(f'<a href="{n.link}" target="_blank" class="n-title">{n.title}</a><div class="n-meta">{n.published}</div>', unsafe_allow_html=True)
    with n_col2:
        st.subheader("🇺🇸 米国経済")
        news_us = fetch_news("米国株 FRB")
        for n in news_us[:10]:
            st.markdown(f'<a href="{n.link}" target="_blank" class="n-title">{n.title}</a><div class="n-meta">{n.published}</div>', unsafe_allow_html=True)

# --- Tab 3: カレンダー ---
with tabs[2]:
    st.subheader("JST カレンダー")
    df_cal = pd.DataFrame([
        {"日時(JST)": "2024-05-15 21:30", "国": "US", "イベント": "米CPI発表"},
        {"日時(JST)": "2024-05-24 08:30", "国": "JP", "イベント": "日本CPI発表"}
    ] + get_earnings_calendar()).sort_values("日時(JST)")
    st.dataframe(df_cal, use_container_width=True)

# --- Tab 4: FIREシミュレーター ---
with tabs[3]:
    f_in, f_out = st.columns([1, 2])
    with f_in:
        st.subheader("条件設定")
        age = st.number_input("現在の年齢", 18, 80, 30)
        
        # 特定口座入力を復活
        st.markdown("**現在の資産**")
        c_reg = st.number_input("特定口座 (万円)", 0.0, 100000.0, 400.0, step=0.1)
        c_nisa = st.number_input("NISA口座 (万円)", 0.0, 100000.0, 100.0, step=0.1)
        st.info(f"合計資産: {c_reg + c_nisa:,.1f}万円")
        
        m_inv = st.number_input("毎月の積立額 (万円)", 0.0, 100.0, 10.0, step=0.1)
        
        st.markdown("**期待利回り (%)**")
        r_pre = st.number_input("積立期 (通常)", 0.0, 20.0, 5.0, step=0.1)
        r_post = st.number_input("リタイア後 (通常)", 0.0, 20.0, 3.0, step=0.1)
        r_bull = st.number_input("強気時 上乗せ", 0.0, 10.0, 2.0, step=0.1)
        r_bear = st.number_input("弱気時 下振れ", 0.0, 10.0, 2.0, step=0.1)
        
        f_age = st.number_input("FIRE年齢", 18, 100, st.session_state.fire_age_val)
        ret_al = st.number_input("想定退職金 (万円)", 0.0, 10000.0, 0.0, step=0.1)
        p_age = st.number_input("年金開始年齢", 60, 75, 65)
        p_val = st.number_input("年金月額 (万円)", 0.0, 50.0, 15.0, step=0.1)
        l_exp = st.number_input("FIRE後生活費 (月額/万円)", 0.0, 200.0, 25.0, step=0.1)
        inf = st.number_input("想定インフレ率 (%)", 0.0, 10.0, 1.0, step=0.1)
        
        show_scen = st.multiselect("表示シナリオ", ["通常", "強気", "弱気"], default=["通常", "強気", "弱気"])

    with f_out:
        sim = FIRESimulator()
        all_res = sim.calculate({
            'currentAge': age, 'currentAssets': c_reg + c_nisa, 'nisaAssets': c_nisa,
            'monthlyInvestment': m_inv, 'expectedReturnPre': r_pre, 'expectedReturnPost': r_post,
            'expectedReturnPreBull': r_pre + r_bull, 'expectedReturnPostBull': r_post + r_bull,
            'expectedReturnPreBear': max(0, r_pre - r_bear), 'expectedReturnPostBear': max(0, r_post - r_bear),
            'fireAge': f_age, 'livingExpense': l_exp, 'inflationRate': inf,
            'pensionAmount': p_val, 'pensionAge': p_age, 'retirementAllowance': ret_al
        })
        
        fig = go.Figure()
        clrs = {"通常": "#58a6ff", "強気": "#00ff00", "弱気": "#ff3333"}
        for n in show_scen:
            df_h = pd.DataFrame(all_res[n]['history'])
            fig.add_trace(go.Scatter(x=df_h['age'], y=df_h['totalAssets'], name=n, line=dict(color=clrs[n], width=3)))
        
        fig.update_layout(title="将来資産推移シミュレーション", xaxis_title="年齢", yaxis_title="資産額 (万円)", template="plotly_dark", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
        
        # 診断レポート（タイル形式で強調）
        st.subheader("📋 シミュレーション診断レポート")
        rep_cols = st.columns(3)
        for idx, n in enumerate(show_scen):
            r = all_res[n]
            with rep_cols[idx]:
                st.markdown(f"""
                <div class="report-panel">
                    <div style="font-weight:700; color:{clrs[n]};">{n}シナリオ</div>
                    <div style="font-size:0.9rem; margin-top:5px;">
                        {'✅ 100歳まで安泰' if not r['exhaustionAge'] else f'⚠️ {r["exhaustionAge"]}歳で枯渇'}
                    </div>
                    <div style="font-size:0.75rem; color:#888;">100歳時: {r['finalAssets']:,.0f}万円</div>
                </div>
                """, unsafe_allow_html=True)

        if st.button("🖼 結果をJPEGで保存"):
            buf = io.BytesIO()
            fig.write_image(buf, format="jpg", width=1200, height=800)
            st.download_button(label="画像をダウンロード", data=buf.getvalue(), file_name="wealth_compass_fire.jpg", mime="image/jpeg")
