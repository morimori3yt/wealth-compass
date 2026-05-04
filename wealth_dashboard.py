import streamlit as st
import streamlit.components.v1 as components
import feedparser
import urllib.parse
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
from simulation_logic import FIRESimulator
import datetime
from dateutil import parser
import time

# --- ページ設定 ---
st.set_page_config(
    page_title="資産形成の羅針盤",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- セッション状態の初期化 ---
if 'fire_age_val' not in st.session_state: st.session_state['fire_age_val'] = 50
if 'rev_results' not in st.session_state: st.session_state['rev_results'] = None

# --- デザイン (CSS) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans JP', sans-serif; }
.n-title { font-size: 1.0rem; font-weight: 700; color: #000000 !important; line-height: 1.4; text-decoration: none; display: block; margin-bottom: 2px; }
.n-title:hover { color: #007bff !important; }
.n-meta { font-size: 0.75rem; color: #d9534f; font-weight: 700; margin-bottom: 10px; border-bottom: 1px solid #eeeeee; padding-bottom: 6px; display: flex; align-items: center; gap: 5px; }
.n-time-tag { background: #fff1f0; color: #cf1322; padding: 1px 6px; border-radius: 4px; border: 1px solid #ffa39e; }
.m-card { background: #f8f9fa; border: 1px solid #e9ecef; padding: 10px; border-radius: 6px; text-align: center; margin-bottom: 10px; }
.m-label { font-size: 0.8rem; color: #6c757d; }
.m-price { font-size: 1.2rem; font-weight: 700; color: #212529; }
.m-up { color: #28a745; }
.m-down { color: #dc3545; }
.rev-panel { background: #eef2f7; padding: 15px; border-radius: 8px; border: 1px solid #d1d9e6; margin-top: 10px; }
.guide-box { background: #ffffff; border: 1px solid #e0e0e0; padding: 15px; border-radius: 8px; margin-bottom: 20px; font-size: 0.85rem; }
.guide-title { font-weight: 700; color: #333; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 5px; display: flex; align-items: center; }
.guide-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; }
.guide-item { color: #555; }
.guide-item b { color: #007bff; }
</style>
""", unsafe_allow_html=True)

# --- 関数群 ---

def get_relative_time(published_str):
    try:
        pub_date = parser.parse(published_str)
        now = datetime.datetime.now(datetime.timezone.utc)
        diff = now - pub_date
        seconds = diff.total_seconds()
        if seconds < 60: return "たった今"
        if seconds < 3600: return f"{int(seconds // 60)}分前"
        if seconds < 86400: return f"{int(seconds // 3600)}時間前"
        return f"{int(seconds // 86400)}日前"
    except: return "不明"

@st.cache_data(ttl=600)
def fetch_latest_news(region):
    """
    ハイブリッド型ニュース取得 (対策A + 対策C)
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    
    def fetch_rss(query_str):
        encoded = urllib.parse.quote(query_str)
        rss_url = f"https://news.google.com/rss/search?q={encoded}&hl=ja&gl=JP&ceid=JP:ja"
        try:
            feed = feedparser.parse(rss_url)
            return feed.entries
        except: return []

    if region == "JP":
        # 日本の専門ソース
        p_sources = " (site:nikkei.com OR site:reuters.com OR site:bloomberg.co.jp OR site:news.yahoo.co.jp OR site:finance.yahoo.co.jp)"
        p_query = p_sources + " 経済 産業 社会情勢"
        fallback_query = "日本 経済 産業 社会情勢"
    else:
        # 米国の専門ソース（日本語版ドメイン優先：対策A）
        # cnbc.comは日本語版がないためそのままとしつつ、他は.jp系を指定
        p_sources = " (site:bloomberg.co.jp OR site:jp.reuters.com OR site:jp.wsj.com OR site:jp.investing.com OR site:cnbc.com)"
        # キーワードの最適化：対策C
        p_query = p_sources + " 米国経済 景気 FRB 産業 社会情勢"
        fallback_query = "米国 経済 FRB 市場 社会情勢"
    
    # 1. 優先ソースから取得
    all_entries = fetch_rss(p_query)
    
    def filter_entries(entries, hours):
        res = []
        for e in entries:
            try:
                dt = parser.parse(e.published)
                if (now - dt).total_seconds() < (hours * 3600):
                    e['rel_time'] = get_relative_time(e.published)
                    res.append(e)
            except: continue
        return res

    # 24h -> 48h で絞り込み
    final = filter_entries(all_entries, 24)
    if len(final) < 10:
        final = filter_entries(all_entries, 48)
    
    # 2. 10件に満たない場合は一般ニュースから補充
    if len(final) < 10:
        fallback_entries = fetch_rss(fallback_query)
        extra = filter_entries(fallback_entries, 48)
        for e in extra:
            if not any(f['link'] == e['link'] for f in final):
                final.append(e)
                if len(final) >= 10: break
                
    return final[:10]

@st.cache_data(ttl=600)
def get_market_data(ticker_symbol, period="5d"):
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period=period)
        return df
    except: return pd.DataFrame()

# --- アプリメイン ---
st.title("🧭 資産形成の羅針盤")
st.markdown("""<div style="text-align:center; margin:10px 0;"><a href="https://rpx.a8.net/svt/ejp?a8mat=4B3GYD+C0U5KI+2HOM+69P01&rakuten=y&a8ejpredirect=http%3A%2F%2Fhb.afl.rakuten.co.jp%2Fhgc%2F0ea62065.34400275.0ea62066.204f04c0%2Fa26050208529_4B3GYD_C0U5KI_2HOM_69P01%3Fpc%3Dhttp%253A%252F%252Fwww.rakuten.co.jp%252F%26m%3Dhttp%253A%252F%252Fm.rakuten.co.jp%252F" rel="nofollow"><img src="https://hbb.afl.rakuten.co.jp/hsb/0eb4bbc7.e9e6f789.0eb4bbaa.95151395/" border="0"></a></div>""", unsafe_allow_html=True)

tabs = st.tabs(["📊 マーケット状況", "📰 ニュース", "📅 カレンダー", "🚀 FIREシミュレーター"])

# --- Tab 1: マーケット ---
with tabs[0]:
    indices = {"日経平均": "^N225", "TOPIX": "^TPX", "NYダウ": "^DJI", "S&P 500": "^GSPC", "ナスダック": "^IXIC", "ドル円": "JPY=X"}
    cols = st.columns(3)
    for idx, (name, symbol) in enumerate(indices.items()):
        with cols[idx % 3]:
            df = get_market_data(symbol)
            if not df.empty:
                curr = df['Close'].iloc[-1]; diff = curr - df['Close'].iloc[-2]; pct = (diff / df['Close'].iloc[-2]) * 100
                cls = "m-up" if diff >= 0 else "m-down"; sign = "+" if diff >= 0 else ""
                st.markdown(f'<div class="m-card"><div class="m-label">{name}</div><div class="m-price">{curr:,.2f}</div><div class="{cls}">{sign}{diff:,.2f} ({sign}{pct:.2f}%)</div></div>', unsafe_allow_html=True)
                fig = px.line(df, x=df.index, y='Close', template="plotly_white", height=80)
                fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), xaxis_visible=False, yaxis_visible=False)
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# --- Tab 2: ニュース (ハイブリッド版) ---
with tabs[1]:
    st.subheader("📰 最新経済ニュース (24時間以内に自動更新)")
    n_c1, n_c2 = st.columns(2)
    with n_c1:
        st.markdown("### 🇯🇵 日本: 経済・産業・社会情勢")
        jp_news = fetch_latest_news("JP")
        if jp_news:
            for n in jp_news:
                st.markdown(f'<a href="{n.link}" target="_blank" class="n-title">{n.title}</a><div class="n-meta"><span class="n-time-tag">⏱ {n.rel_time}</span> | {n.source.get("title", "Google News")}</div>', unsafe_allow_html=True)
        else: st.info("現在、表示できる最新ニュースはありません。")
    with n_c2:
        st.markdown("### 🇺🇸 米国: 経済・産業・社会情勢")
        us_news = fetch_latest_news("US")
        if us_news:
            for n in us_news:
                st.markdown(f'<a href="{n.link}" target="_blank" class="n-title">{n.title}</a><div class="n-meta"><span class="n-time-tag">⏱ {n.rel_time}</span> | {n.source.get("title", "Google News")}</div>', unsafe_allow_html=True)
        else: st.info("現在、表示できる最新ニュースはありません。")

# --- Tab 3: カレンダー ---
with tabs[2]:
    st.subheader("📅 経済指標カレンダー")
    st.markdown("""
    <div class="guide-box">
        <div class="guide-title">📊 凡例 (数値の見方)</div>
        <div style="display: flex; gap: 20px; margin-bottom: 15px;">
            <span><b>Actual (結果):</b> 今回発表された確定値</span>
            <span><b>Forecast (予想):</b> 市場関係者の事前予測</span>
            <span><b>Previous (前回):</b> 前回の発表数値</span>
        </div>
        <div class="guide-title">🔤 主要指標の日本語訳ガイド</div>
        <div class="guide-grid">
            <div class="guide-item"><b>Non-Farm Payrolls:</b> 非農業部門雇用者数</div>
            <div class="guide-item"><b>Unemployment Rate:</b> 失業率</div>
            <div class="guide-item"><b>CPI (y/y):</b> 消費者物価指数 (前年比)</div>
            <div class="guide-item"><b>Retail Sales:</b> 小売売上高</div>
            <div class="guide-item"><b>GDP:</b> 国内総生産</div>
            <div class="guide-item"><b>Interest Rate:</b> 政策金利 (FOMC等)</div>
            <div class="guide-item"><b>Core CPI:</b> コア物価指数 (変動激しい食品除外)</div>
            <div class="guide-item"><b>Initial Jobless Claims:</b> 新規失業保険申請件数</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    tv_widget_html = """
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
      { "colorTheme": "light", "isMaximized": true, "width": "100%", "height": "800", "locale": "ja", "importanceFilter": "-1,0,1", "countryFilter": "jp,us,eu,gb,au,ca" }
      </script>
    </div>
    """
    components.html(tv_widget_html, height=820, scrolling=True)

# --- Tab 4: FIREシミュレーター ---
with tabs[3]:
    f_in, f_out = st.columns([1, 2])
    with f_in:
        st.subheader("条件設定")
        age = st.number_input("現在の年齢", 18, 80, 30)
        c_reg = st.number_input("特定口座 (万円)", 0.0, 100000.0, 400.0)
        c_nisa = st.number_input("NISA口座 (万円)", 0.0, 100000.0, 100.0)
        nisa_rem = st.number_input("NISA投資枠の残り (万円)", 0.0, 1800.0, 1700.0)
        total_curr = c_reg + c_nisa
        st.markdown(f"**現在の資産額合計: {total_curr:,.1f} 万円**")
        m_inv = st.number_input("毎月の積立額 (万円)", 0.0, 100.0, 10.0)
        st.markdown("**期待利回り (%)**")
        r_pre = st.number_input("積立期利回り (%)", 0.0, 20.0, 5.0)
        r_post = st.number_input("FIRE後利回り (%)", 0.0, 20.0, 3.0)
        r_bull = st.number_input("強気時上乗せ (%)", 0.0, 10.0, 2.0)
        r_bear = st.number_input("弱気時下振れ (%)", 0.0, 10.0, 2.0)
        tax_rate = st.number_input("特定口座の税率 (%)", 0.0, 100.0, 20.315, step=0.001, format="%.3f")
        f_age = st.number_input("FIRE年齢", 18, 100, st.session_state['fire_age_val'])
        ret_al = st.number_input("想定退職金 (万円)", 0.0, 10000.0, 0.0)
        p_age = st.number_input("年金開始年齢", 60, 75, 65)
        p_val = st.number_input("年金月額 (万円)", 0.0, 50.0, 15.0)
        l_exp = st.number_input("生活費 (月額/万円)", 0.0, 200.0, 25.0)
        inf = st.number_input("想定インフレ率 (%)", 0.0, 10.0, 1.0)
        show_scen = st.multiselect("シナリオ表示", ["通常", "強気", "弱気"], default=["通常", "強気", "弱気"])
        st.divider()
        if st.button("✨ 最短FIRE年齢を計算する", use_container_width=True):
            sim_rev = FIRESimulator()
            st.session_state['rev_results'] = sim_rev.find_all_fire_ages({'currentAge': age, 'currentAssets': total_curr, 'nisaAssets': c_nisa, 'nisaLimitRemaining': nisa_rem, 'taxRate': tax_rate, 'monthlyInvestment': m_inv, 'expectedReturnPre': r_pre, 'expectedReturnPost': r_post, 'expectedReturnPreBull': r_pre + r_bull, 'expectedReturnPostBull': r_post + r_bull, 'expectedReturnPreBear': max(0, r_pre - r_bear), 'expectedReturnPostBear': max(0, r_post - r_bear), 'livingExpense': l_exp, 'inflationRate': inf, 'pensionAmount': p_val, 'pensionAge': p_age, 'retirementAllowance': ret_al})
        if st.session_state['rev_results']:
            res = st.session_state['rev_results']
            st.markdown(f'<div class="rev-panel"><div style="font-weight:700; margin-bottom:8px; border-bottom:1px solid #ccc;">最短FIRE可能年齢</div><div style="color:#28a745;">🚀 強気: <b>{res["強気"] if res["強気"] else "不可"}歳</b></div><div style="color:#58a6ff;">📊 通常: <b>{res["通常"] if res["通常"] else "不可"}歳</b></div><div style="color:#dc3545;">⚠️ 弱気: <b>{res["弱気"] if res["弱気"] else "不可"}歳</b></div></div>', unsafe_allow_html=True)
            if res['通常'] and st.button("通常結果を適用"): st.session_state['fire_age_val'] = res['通常']; st.rerun()

    with f_out:
        sim = FIRESimulator()
        all_res = sim.calculate({'currentAge': age, 'currentAssets': total_curr, 'nisaAssets': c_nisa, 'nisaLimitRemaining': nisa_rem, 'taxRate': tax_rate, 'monthlyInvestment': m_inv, 'expectedReturnPre': r_pre, 'expectedReturnPost': r_post, 'expectedReturnPreBull': r_pre + r_bull, 'expectedReturnPostBull': r_post + r_bull, 'expectedReturnPreBear': max(0, r_pre - r_bear), 'expectedReturnPostBear': max(0, r_post - r_bear), 'fireAge': f_age, 'livingExpense': l_exp, 'inflationRate': inf, 'pensionAmount': p_val, 'pensionAge': p_age, 'retirementAllowance': ret_al})
        fig = go.Figure()
        clrs = {"通常": "#58a6ff", "強気": "#28a745", "弱気": "#dc3545"}
        for n in show_scen:
            df_h = pd.DataFrame(all_res[n]['history'])
            fig.add_trace(go.Scatter(x=df_h['age'], y=df_h['totalAssets'], name=n, line=dict(color=clrs[n], width=3), customdata=df_h['age'], hovertemplate="%{customdata}歳<br>資産: %{y:,.0f} 万円<extra></extra>"))
        fig.update_layout(title="将来資産推移", xaxis_title="年齢", yaxis_title="資産額 (万円)", template="plotly_white", hovermode="x unified", xaxis=dict(hoverformat=".0f歳"))
        st.plotly_chart(fig, use_container_width=True)
        st.subheader("📋 シミュレーション診断レポート")
        rep_cols = st.columns(3)
        for idx, n in enumerate(show_scen):
            r = all_res[n]
            with rep_cols[idx]: st.markdown(f'<div style="background:#f8f9fa; padding:10px; border-radius:6px; border:1px solid #ddd; text-align:center;"><div style="font-weight:700; color:{clrs[n]};">{n}シナリオ</div><div style="font-weight:700; color:#333;">{"✅ 100歳まで安泰" if not r["exhaustionAge"] else f"⚠️ {r["exhaustionAge"]}歳で枯渇"}</div><div style="font-weight:700; color:#333;">100歳時: {r["finalAssets"]:,.0f}万円</div></div>', unsafe_allow_html=True)
