import streamlit as st
import feedparser
import urllib.parse
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
from simulation_logic import FIRESimulator
import datetime
import calendar
import io

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
.n-title { font-size: 1.05rem; font-weight: 700; color: #000000 !important; line-height: 1.4; text-decoration: none; display: block; margin-bottom: 4px; }
.n-meta { font-size: 0.75rem; color: #666666; margin-bottom: 12px; border-bottom: 1px solid #eeeeee; padding-bottom: 8px; }
.m-card { background: #f8f9fa; border: 1px solid #e9ecef; padding: 10px; border-radius: 6px; text-align: center; margin-bottom: 10px; }
.m-label { font-size: 0.8rem; color: #6c757d; }
.m-price { font-size: 1.2rem; font-weight: 700; color: #212529; }
.m-up { color: #28a745; }
.m-down { color: #dc3545; }
.rev-panel { background: #eef2f7; padding: 15px; border-radius: 8px; border: 1px solid #d1d9e6; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

# --- カレンダーデータ取得・算出エンジン (最終版) ---

@st.cache_data(ttl=3600*12)
def fetch_calendar_data(sel_year, sel_month):
    events = []
    
    # 1. 経済指標 (高精度推計)
    def add_eco(day, cat, content):
        if 1 <= day <= 31:
            events.append({"日付": f"{sel_year}-{sel_month:02d}-{day:02d}", "カテゴリ": cat, "内容": content})

    cal_obj = calendar.Calendar(firstweekday=calendar.SUNDAY)
    month_days = cal_obj.monthdays2calendar(sel_year, sel_month)
    f_fri = -1
    for week in month_days:
        for d, dow in week:
            if d != 0 and dow == calendar.FRIDAY: f_fri = d; break
        if f_fri != -1: break
    if f_fri != -1: add_eco(f_fri, "米国経済指標", "米雇用統計")
    add_eco(12, "米国経済指標", "米CPI (消費者物価指数)")
    add_eco(15, "米国経済指標", "米小売売上高")
    if sel_month in [1, 3, 5, 6, 7, 9, 11, 12]: add_eco(20, "米国経済指標", "FOMC (政策金利発表)")
    add_eco(1, "日本経済指標", "日銀短観")
    add_eco(20, "日本経済指標", "日本CPI (消費者物価指数)")
    add_eco(25, "日本経済指標", "日銀金融政策決定会合")

    # 2. 決算スケジュール (Ticker.earnings_dates方式へ刷新)
    # 取得効率と成功率を重視した主要銘柄リスト
    tickers_jp = ["7203.T", "6758.T", "8306.T", "9984.T", "6861.T", "4063.T", "8035.T", "9432.T"]
    tickers_us = ["AAPL", "MSFT", "NVDA", "AMZN", "TSLA", "META", "GOOGL", "NFLX", "AMD"]
    
    all_tickers = [(t, "日本株決算") for t in tickers_jp] + [(t, "米国株決算") for t in tickers_us]
    
    for symbol, cat in all_tickers:
        try:
            t = yf.Ticker(symbol)
            # より populated な earnings_dates を使用
            ed_df = t.earnings_dates
            if ed_df is not None and not ed_df.empty:
                for ed_idx in ed_df.index:
                    if ed_idx.year == sel_year and ed_idx.month == sel_month:
                        events.append({"日付": ed_idx.strftime('%Y-%m-%d'), "カテゴリ": cat, "内容": f"{symbol.replace('.T','')} 決算"})
        except: continue
            
    return pd.DataFrame(events)

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

# --- コンテンツ構成 ---
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

# --- Tab 2: ニュース ---
with tabs[1]:
    n_c1, n_c2 = st.columns(2)
    with n_c1:
        st.subheader("🇯🇵 日本経済")
        for n in fetch_news("日本株 経済")[:8]:
            st.markdown(f'<a href="{n.link}" target="_blank" class="n-title">{n.title}</a><div class="n-meta">{n.published}</div>', unsafe_allow_html=True)
    with n_c2:
        st.subheader("🇺🇸 米国経済")
        for n in fetch_news("米国株 FRB")[:8]:
            st.markdown(f'<a href="{n.link}" target="_blank" class="n-title">{n.title}</a><div class="n-meta">{n.published}</div>', unsafe_allow_html=True)

# --- Tab 3: カレンダー ---
with tabs[2]:
    st.subheader("経済・決算カレンダー")
    now = datetime.datetime.now()
    y_range = list(range(2020, now.year + 2))
    sel_y = st.selectbox("年を選択", y_range, index=y_range.index(now.year))
    sel_m = st.selectbox("月を選択", range(1, 13), index=now.month - 1)
    
    f_c1, f_c2, f_c3, f_c4 = st.columns(4)
    show_us_eco = f_c1.checkbox("米国経済指標", value=True)
    show_us_ear = f_c2.checkbox("米国株決算", value=True)
    show_jp_eco = f_c3.checkbox("日本経済指標", value=True)
    show_jp_ear = f_c4.checkbox("日本株決算", value=True)
    
    with st.spinner("最新スケジュールを同期中..."):
        df_cal = fetch_calendar_data(sel_y, sel_m)
    
    if not df_cal.empty:
        active_cats = []
        if show_us_eco: active_cats.append("米国経済指標")
        if show_us_ear: active_cats.append("米国株決算")
        if show_jp_eco: active_cats.append("日本経済指標")
        if show_jp_ear: active_cats.append("日本株決算")
        display_cal = df_cal[df_cal['カテゴリ'].isin(active_cats)].sort_values("日付")
        if not display_cal.empty:
            # 謎の数字（インデックス）を非表示にして表示
            st.dataframe(display_cal, use_container_width=True, hide_index=True)
        else: st.info("表示する予定はありません。")
    else: st.info("予定は見つかりませんでした。")

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
