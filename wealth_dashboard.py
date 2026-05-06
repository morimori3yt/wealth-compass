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
    initial_sidebar_state="collapsed"
)

# --- セッション状態の初期化 ---
if 'fire_age_val' not in st.session_state: st.session_state['fire_age_val'] = 50
if 'rev_results' not in st.session_state: st.session_state['rev_results'] = None

# --- 資産マスターリスト ---

# 1. 配置変更 (資産マスターリスト)
ASSET_MASTER = {
    # 株式指数 (日本・アジア)
    "日経平均": "^N225", "TOPIX": "^TPX", "マザーズ": "250.T", 
    "上海総合": "000001.SS", "香港ハンセン": "^HSI", "台湾加権": "^TWII", "インドSensex": "^BSESN",
    # 株式指数 (米国・欧州)
    "NYダウ": "^DJI", "S&P 500": "^GSPC", "ナスダック": "^IXIC", "NASDAQ 100": "^NDX", "SOX指数": "^SOX", "FANG+": "FNGS", "ラッセル2000": "^RUT", "VIX恐怖指数": "^VIX",
    "DAX (独)": "^GDAXI", "FTSE (英)": "^FTSE", "CAC (仏)": "^FCHI", "SMI (瑞)": "^SSMI",
    # 為替
    "ドル円": "JPY=X", "ユーロ円": "EURJPY=X", "ポンド円": "GBPJPY=X", "豪ドル円": "AUDJPY=X", 
    "ユーロドル": "EURUSD=X", "ポンドドル": "GBPUSD=X",
    # 商品 (コモディティ)
    "金先物": "GC=F", "銀先物": "SI=F", "銅先物": "HG=F", "プラチナ": "PL=F", 
    "WTI原油": "CL=F", "天然ガス": "NG=F",
    # 仮想通貨
    "ビットコイン": "BTC-USD", "イーサリアム": "ETH-USD", "XRP (リップル)": "XRP-USD",
    # 金利
    "米10年債利回り": "^TNX", "米30年債利回り": "^TYX"
}

default_assets = [
    "日経平均", "TOPIX", "NYダウ", "S&P 500", "ナスダック", "SOX指数", "ドル円", "ビットコイン",
    "NASDAQ 100", "FANG+", "VIX恐怖指数", "ユーロ円", "金先物", "WTI原油", "米10年債利回り", "上海総合"
]

# --- 関数群 ---

@st.cache_data(ttl=300)
def get_intraday_market_data(ticker_symbol):
    is_topix = (ticker_symbol == "^TPX")
    if is_topix:
        # yfinanceのTOPIXデータ配信停止問題を回避するため、連動ETFで波形を取得
        ticker_symbol = "1306.T"
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period="5d", interval="15m")
        if df.empty:
            return None, None, None
            
        df['date'] = df.index.date
        latest_date = df['date'].iloc[-1]
        
        df_today = df[df['date'] == latest_date].copy()
        df_prev = df[df['date'] < latest_date]
        
        curr_price = df_today['Close'].iloc[-1]
        if not df_prev.empty:
            prev_close = df_prev['Close'].iloc[-1]
        else:
            prev_close = df_today['Close'].iloc[0]

        if is_topix:
            # 最新のTOPIX水準(約2750)とETF(約2900)の比率を掛けて、ダミーのTOPIX数値を合成
            ratio = 0.95 
            df_today['Close'] = df_today['Close'] * ratio
            curr_price *= ratio
            prev_close *= ratio
            
        return df_today, curr_price, prev_close
    except: 
        return None, None, None

def render_market_tile(name, symbol):
    import plotly.graph_objects as go
    
    df_today, curr, prev = get_intraday_market_data(symbol)
    if df_today is None or df_today.empty:
        st.markdown(f'<div class="m-tile" style="background: {theme_card}; color: {theme_text};"><div class="m-tile-inner"><div class="m-tile-left"><div class="m-tile-name">{name}</div></div><div class="m-tile-right"><div class="m-tile-price">-</div><div class="m-tile-diff">取得失敗</div></div></div></div>', unsafe_allow_html=True)
        return

    diff = curr - prev
    pct = (diff / prev) * 100 if prev != 0 else 0
    is_up = diff >= 0
    
    # 世界の株価風：背景色ヒートマップロジック
    if "日本式" in color_pattern:
        bg_up = "#4d0000" if is_dark else "#ffcccc"
        bg_down = "#004d00" if is_dark else "#ccffcc"
        line_up = "#ff6666" if is_dark else "#ff0000"
        line_down = "#66ff66" if is_dark else "#008000"
    else:
        bg_up = "#004d00" if is_dark else "#ccffcc"
        bg_down = "#4d0000" if is_dark else "#ffcccc"
        line_up = "#66ff66" if is_dark else "#008000"
        line_down = "#ff6666" if is_dark else "#ff0000"

    tile_bg = bg_up if is_up else bg_down
    chart_line = line_up if is_up else line_down
    text_col = "#ffffff" if is_dark else "#000000"
    
    sign = "+" if is_up else ""
    fmt = ",.3f" if ("JPY" in symbol or "^TNX" in symbol or "^TYX" in symbol) else ",.2f"
    
    with st.container():
        st.markdown(f"""
        <div class="m-tile" style="background-color: {tile_bg}; color: {text_col};">
            <div class="m-tile-inner">
                <div class="m-tile-left">
                    <div class="m-tile-name">{name}</div>
                </div>
                <div class="m-tile-right">
                    <div class="m-tile-price">{curr:{fmt}}</div>
                    <div class="m-tile-diff">
                        {sign}{diff:{fmt}} ({sign}{pct:.2f}%)
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Area Chart用の半透明塗りつぶし色を計算
        h = chart_line.lstrip('#')
        fill_rgba = f"rgba({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}, 0.4)"
        
        # 24時間(イントラデイ) Area Chart
        fig = go.Figure()
        
        # 前日終値の基準線を透明な線として追加（Fillのベース）
        fig.add_trace(go.Scatter(x=df_today.index, y=[prev]*len(df_today), mode='lines', line=dict(color='rgba(0,0,0,0)', width=0), hoverinfo='skip'))
        
        # 現在のラインと、基準線に向けた塗りつぶし (tonexty)
        fig.add_trace(go.Scatter(x=df_today.index, y=df_today['Close'], mode='lines', line=dict(color=chart_line, width=1.5), fill='tonexty', fillcolor=fill_rgba, hoverinfo='skip'))
        
        # 前日終値の基準線 (ホリゾンタルライン) を明示的に引く
        hline_color = "rgba(255,255,255,0.4)" if is_dark else "rgba(0,0,0,0.3)"
        fig.add_hline(y=prev, line_dash="dash", line_color=hline_color, opacity=1.0, line_width=1.5)
        
        min_y = min(df_today['Close'].min(), prev)
        max_y = max(df_today['Close'].max(), prev)
        padding = (max_y - min_y) * 0.1
        if padding == 0: padding = curr * 0.001
        
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis_visible=False, yaxis_visible=False,
            yaxis=dict(range=[min_y - padding, max_y + padding]),
            height=40,
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
            hovermode=False
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

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
    now = datetime.datetime.now(datetime.timezone.utc)
    def fetch_rss(query_str):
        encoded = urllib.parse.quote(query_str)
        rss_url = f"https://news.google.com/rss/search?q={encoded}&hl=ja&gl=JP&ceid=JP:ja"
        try:
            feed = feedparser.parse(rss_url)
            return feed.entries
        except: return []

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

    jp_keywords = "日本 (経済 OR 産業 OR 社会情勢 OR 景気 OR 金融緩和 OR 日銀)"
    us_keywords = "米国 (経済 OR 景気 OR FRB OR 産業 OR 社会情勢 OR 雇用統計 OR ナスダック OR S&P500 OR 半導体 OR インフレ OR 労働市場)"
    jp_p_sources = " (site:nikkei.com OR site:reuters.com OR site:bloomberg.co.jp OR site:news.yahoo.co.jp OR site:finance.yahoo.co.jp)"
    us_p_sources = " (site:bloomberg.co.jp OR site:jp.reuters.com OR site:jp.wsj.com OR site:jp.investing.com OR site:cnbc.com OR site:nikkei.com OR site:finance.yahoo.co.jp)"

    if region == "JP":
        p_query = jp_p_sources + " " + jp_keywords
        f_query = jp_keywords
    else:
        p_query = us_p_sources + " " + us_keywords
        f_query = us_keywords

    entries = fetch_rss(p_query)
    final = filter_entries(entries, 24)
    if len(final) < 10: final = filter_entries(entries, 48)
    if len(final) < 10:
        fallback_entries = fetch_rss(f_query)
        extra = filter_entries(fallback_entries, 72)
        for e in extra:
            if not any(f['link'] == e['link'] for f in final):
                final.append(e); 
                if len(final) >= 10: break
    return final[:10]

# --- アプリメイン ---
st.title("🧭 資産形成の羅針盤")
st.markdown("""<div style="text-align:center; margin:10px 0;"><a href="https://rpx.a8.net/svt/ejp?a8mat=4B3GYD+C0U5KI+2HOM+69P01&rakuten=y&a8ejpredirect=http%3A%2F%2Fhb.afl.rakuten.co.jp%2Fhgc%2F0ea62065.34400275.0ea62066.204f04c0%2Fa26050208529_4B3GYD_C0U5KI_2HOM_69P01%3Fpc%3Dhttp%253A%252F%252Fwww.rakuten.co.jp%252F%26m%3Dhttp%253A%252F%252Fm.rakuten.co.jp%252F" rel="nofollow"><img src="https://hbb.afl.rakuten.co.jp/hsb/0eb4bbc7.e9e6f789.0eb4bbaa.95151395/" border="0"></a></div>""", unsafe_allow_html=True)

tabs = st.tabs(["📊 マーケット状況", "📰 ニュース", "📅 カレンダー", "🚀 FIREシミュレーター"])

# --- Tab 1: マーケット (世界の株価風・カスタマイズ版) ---
with tabs[0]:
    with st.expander("⚙️ 表示設定（項目変更・カラーテーマ）", expanded=False):
        selected_assets = st.multiselect("表示項目・順序の変更", options=list(ASSET_MASTER.keys()), default=default_assets)
        bg_mode = st.radio("背景色設定", ["明るい (白)", "暗い (黒)"], horizontal=True)
        color_pattern = st.radio("騰落カラー設定", ["日本式 (上昇:赤 / 下落:緑)", "欧米式 (上昇:緑 / 下落:赤)"], horizontal=True)

    # カラーコード定義
    is_dark = bg_mode == "暗い (黒)"
    theme_bg = "#121212" if is_dark else "#ffffff"
    theme_card = "#1e1e1e" if is_dark else "#f8f9fa"
    theme_text = "#ffffff" if is_dark else "#212529"
    theme_border = "#333333" if is_dark else "#e9ecef"

    # カスタムCSSインジェクション
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&family=Roboto+Mono:wght@500&display=swap');
    html, body, [class*="css"] {{ font-family: 'Noto Sans JP', sans-serif; }}

    div[data-testid="column"] {{ padding: 2px !important; }}

    .m-tile {{
        border: 1px solid {theme_border};
        padding: 4px 6px 0px 6px;
        border-radius: 2px;
        margin-bottom: 2px;
        transition: transform 0.1s;
    }}
    .m-tile:hover {{ transform: scale(1.02); z-index: 10; position: relative; border-color: #aaa; box-shadow: 0 0 10px rgba(0,0,0,0.3); }}

    .m-tile-inner {{ display: flex; justify-content: space-between; align-items: center; width: 100%; }}
    .m-tile-left {{ text-align: left; padding-top: 2px; }}
    .m-tile-right {{ text-align: right; }}

    .m-tile-name {{ font-size: 0.85rem; font-weight: 700; line-height: 1.1; margin-bottom: 0px; }}
    .m-tile-price {{ font-family: 'Roboto Mono', monospace; font-size: 1.25rem; font-weight: 700; line-height: 1.0; margin-bottom: 1px; }}
    .m-tile-diff {{ font-size: 0.8rem; font-weight: 700; line-height: 1.0; margin-bottom: 0px; }}
    </style>
    """, unsafe_allow_html=True)

    st.subheader("🌎 グローバル・マーケット・ボード")
    
    # グリッドレイアウト
    if not selected_assets:
        st.info("サイドバーから表示したい資産を選択してください。")
    else:
        # 4列のグリッド
        cols = st.columns(4)
        for idx, name in enumerate(selected_assets):
            with cols[idx % 4]:
                render_market_tile(name, ASSET_MASTER[name])

# --- Tab 2: ニュース ---
with tabs[1]:
    st.subheader("📰 最新経済ニュース (自動更新)")
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
