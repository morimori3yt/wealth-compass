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
    page_title="資産形成の羅針盤 | 不労所得カウンター・日本版 Fear & Greed Index・暴落シミュレーター",
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
    # 株式指数 (米国・欧州・グローバル)
    "NYダウ": "^DJI", "S&P 500": "^GSPC", "ナスダック": "^IXIC", "NASDAQ 100": "^NDX", "SOX指数": "^SOX", "FANG+": "FNGS", "ラッセル2000": "^RUT", "VIX恐怖指数": "^VIX",
    "オルカン (ACWI)": "ACWI",
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
    "日経平均", "TOPIX", "NYダウ", "S&P 500", "オルカン (ACWI)", "SOX指数", "ドル円", "ビットコイン",
    "NASDAQ 100", "FANG+", "VIX恐怖指数", "ユーロ円", "金先物", "WTI原油", "米10年債利回り", "上海総合"
]

# --- 共通ユーティリティ ---
def get_share_button_html(text, url="https://wealth-compass.streamlit.app/"):
    import urllib.parse
    encoded_text = urllib.parse.quote(text)
    encoded_url = urllib.parse.quote(url)
    share_url = f"https://twitter.com/intent/tweet?text={encoded_text}&url={encoded_url}"
    return f'''
        <div style="display: flex; align-items: center; justify-content: flex-end; gap: 12px; margin-top: 12px; flex-wrap: wrap;">
            <span style="font-size: 0.75rem; color: #64748B; font-family: 'Inter', sans-serif;">📸 スクリーンショットを撮って一緒に投稿しましょう</span>
            <a href="{share_url}" target="_blank" style="background-color: #000000; color: #ffffff; text-decoration: none; padding: 8px 16px; border-radius: 20px; font-size: 0.85rem; font-weight: 600; display: inline-flex; align-items: center; gap: 6px; white-space: nowrap;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
                結果をXでシェア
            </a>
        </div>
    '''

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
    
    if "日本式" in color_pattern:
        color_up, color_down = "#EF4444", "#10B981"
        bg_up, bg_down = "rgba(239, 68, 68, 0.15)", "rgba(16, 185, 129, 0.15)"
    else:
        color_up, color_down = "#10B981", "#EF4444"
        bg_up, bg_down = "rgba(16, 185, 129, 0.15)", "rgba(239, 68, 68, 0.15)"

    chart_line = color_up if is_up else color_down
    badge_bg = bg_up if is_up else bg_down
    sign = "+" if is_up else ""
    fmt = ",.3f" if ("JPY" in symbol or "^TNX" in symbol or "^TYX" in symbol) else ",.2f"
    
    # タイルとチャートを一つの枠で囲む
    st.markdown(f"""
    <div class="m-tile">
        <div class="m-tile-accent" style="background-color: {chart_line};"></div>
        <div class="m-tile-inner" style="margin-bottom: 12px;">
            <div class="m-tile-left">
                <div class="m-tile-name">{name}</div>
            </div>
            <div class="m-tile-right">
                <div class="m-tile-price">{curr:{fmt}}</div>
                <div class="m-tile-badge" style="background-color: {badge_bg}; color: {chart_line};">
                    {sign}{diff:{fmt}} ({sign}{pct:.2f}%)
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # チャート描画 (高さを拡大)
    h = chart_line.lstrip('#')
    fill_rgba = f"rgba({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}, 0.15)"
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_today.index, y=[prev]*len(df_today), mode='lines', line=dict(color='rgba(0,0,0,0)', width=0), hoverinfo='skip'))
    fig.add_trace(go.Scatter(x=df_today.index, y=df_today['Close'], mode='lines', line=dict(color=chart_line, width=2.5), fill='tonexty', fillcolor=fill_rgba, hoverinfo='skip'))
    
    # 基準線
    fig.add_hline(y=prev, line_dash="dash", line_color="rgba(128,128,128,0.5)", line_width=1)
    
    min_y, max_y = min(df_today['Close'].min(), prev), max(df_today['Close'].max(), prev)
    padding = (max_y - min_y) * 0.25 if max_y != min_y else curr * 0.001
    
    fig.update_layout(
        margin=dict(l=40, r=40, t=10, b=10), xaxis_visible=False, 
        yaxis_visible=True,
        yaxis=dict(
            range=[min_y - padding, max_y + padding],
            tickvals=[prev, curr],
            ticktext=[f"前:{prev:{fmt}}", f"現:{curr:{fmt}}"],
            tickfont=dict(size=9, color=theme_muted),
            side="right",
            showgrid=True,
            gridcolor='rgba(128,128,128,0.1)'
        ), 
        height=150, # 縦を大幅に拡大
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False, hovermode=False
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
# 広告リストの読み込みとJavaScriptによるローテーション
def render_rotating_ads():
    default_ads = ["<a href='https://rpx.a8.net/svt/ejp?a8mat=4B3GYD+C0U5KI+2HOM+69P01&rakuten=y&a8ejpredirect=http%3A%2F%2Fhb.afl.rakuten.co.jp%2Fhgc%2F0ea62065.34400275.0ea62066.204f04c0%2Fa26050208529_4B3GYD_C0U5KI_2HOM_69P01%3Fpc%3Dhttp%253A%252F%252Fwww.rakuten.co.jp%252F%26m%3Dhttp%253A%252F%252Fm.rakuten.co.jp%252F' rel='nofollow'><img src='https://hbb.afl.rakuten.co.jp/hsb/0eb4bbc7.e9e6f789.0eb4bbaa.95151395/' border='0'></a>"]
    try:
        df_ads = pd.read_csv('ads_list.csv')
        ad_list = df_ads['html'].dropna().tolist() if not df_ads.empty else default_ads
    except:
        ad_list = default_ads

    # JSでランダム表示 & 60秒ローテーション
    import json
    ads_json = json.dumps(ad_list)
    
    ad_html = f"""
    <style>
        #ad-container {{
            text-align: center;
            transition: opacity 0.3s ease-in-out;
            cursor: pointer;
            width: 100%;
            overflow: hidden;
        }}
        /* 広告内の画像やリンクを強制的に画面幅に収める */
        #ad-container img, #ad-container a, #ad-container div {{
            max-width: 100% !important;
            height: auto !important;
        }}
    </style>
    <div id="ad-container"></div>
    <script>
        const ads = {ads_json};
        const container = document.getElementById('ad-container');
        let currentIndex = -1;
        
        function changeAd() {{
            if (ads.length <= 0) return;
            
            container.style.opacity = 0;
            setTimeout(() => {{
                let nextIndex;
                if (ads.length > 1) {{
                    do {{
                        nextIndex = Math.floor(Math.random() * ads.length);
                    }} while (nextIndex === currentIndex);
                }} else {{
                    nextIndex = 0;
                }}
                
                currentIndex = nextIndex;
                container.innerHTML = ads[currentIndex];
                
                // すべてのリンクを強制的に新しいタブで開くように設定
                const links = container.getElementsByTagName('a');
                for (let link of links) {{
                    link.target = "_blank";
                    link.rel = "noopener noreferrer";
                }}
                
                container.style.opacity = 1;
            }}, 300);
        }}
        
        // 初回表示
        changeAd();
        
        // 10秒ごとに自動切り替え
        setInterval(changeAd, 10000);
        
        // 親画面の操作（タブクリックなど）を検知して即座に切り替える
        try {{
            const blockShortcuts = (e) => {{
                // Cキー単体、またはShift+Cなどのショートカットをブロック（コピー Cmd+C / Ctrl+C は通す）
                if ((e.key.toLowerCase() === 'c') && !e.metaKey && !e.ctrlKey) {{
                    e.stopPropagation();
                }}
            }};
            window.parent.document.addEventListener('click', function(e) {{
                setTimeout(changeAd, 100);
            }}, true);
            window.parent.document.addEventListener('keydown', blockShortcuts, true);
        }} catch (e) {{
            // クロスドメイン制限がある場合でもタイマーは動作し続ける
        }}
    </script>
    """
    
    st.markdown(f"""
        <style>
        .block-container {{
            padding-top: 0.3rem !important;
            padding-bottom: 100px !important;
        }}
        .main-title {{
            font-size: clamp(1.5rem, 6.5vw, 2.8rem);
            font-weight: 800;
            text-align: center;
            margin-bottom: 0.2rem;
            color: #1E293B;
            white-space: nowrap;
            font-family: 'Inter', 'Noto Sans JP', sans-serif;
        }}
        .ad-disclosure {{
            font-size: 0.75rem;
            color: #64748B;
            text-align: center;
            margin-bottom: 0.5rem;
            font-family: 'Inter', 'Noto Sans JP', sans-serif;
        }}
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header {{visibility: hidden;}}
        .stAppDeployButton {{display:none;}}
        div.stToolbar {{display:none;}}
        div[data-testid="stStatusWidget"] {{display:none;}}
        #viewer-link {{display:none;}}
        </style>
        <div class="main-title">🧭 資産形成の羅針盤</div>
        <div class="ad-disclosure">※本ページはプロモーション（アフィリエイト広告）が含まれています</div>
        """, unsafe_allow_html=True)
    
    components.html(ad_html, height=120)

render_rotating_ads()

tabs = st.tabs(["📊 マーケット状況", "📰 ニュース", "🎰 センチメント", "📅 カレンダー", "⏱️ 不労所得", "🚀 FIREシミュレーター", "🌊 暴落テスト"])

# --- Tab 1: マーケット (世界の株価風・カスタマイズ版) ---
with tabs[0]:
    with st.expander("⚙️ 表示設定（項目変更・カラーテーマ）", expanded=True):
        selected_assets_base = st.multiselect("① 表示項目の追加・削除", options=list(ASSET_MASTER.keys()), default=default_assets)
        
        # 状態同期ロジック: 追加/削除とドラッグ順序の保持
        if 'master_order' not in st.session_state:
            st.session_state['master_order'] = default_assets.copy()
            st.session_state['sort_key_suffix'] = 0
            st.session_state['last_selected_set'] = set(default_assets)
            
        current_set = set(selected_assets_base)
        last_set = st.session_state['last_selected_set']
        
        if current_set != last_set:
            removed = last_set - current_set
            added = current_set - last_set
            # 削除された項目を除外（順序は維持）
            new_order = [x for x in st.session_state['master_order'] if x not in removed]
            # 新規項目を末尾に追加
            for x in selected_assets_base:
                if x in added and x not in new_order:
                    new_order.append(x)
                    
            st.session_state['master_order'] = new_order
            st.session_state['last_selected_set'] = current_set
            st.session_state['sort_key_suffix'] += 1 # 強制リロードのためキーを更新

        st.markdown("<div style='font-size:14px; font-weight:600; margin-top:10px; margin-bottom:5px;'>② パネル配置の並び替え（ドラッグ＆ドロップで上下に移動）</div>", unsafe_allow_html=True)
        try:
            from streamlit_sortables import sort_items
            sortable_data = [{'header': '以下の項目をドラッグして並び替えてください', 'items': st.session_state['master_order']}]
            
            # アイテムが増減した時だけ初期化される動的キー
            dyn_key = f"asset_sorter_{st.session_state['sort_key_suffix']}"
            sorted_res = sort_items(sortable_data, key=dyn_key, multi_containers=True)
            
            if sorted_res and len(sorted_res) > 0 and 'items' in sorted_res[0]:
                ordered_assets = sorted_res[0]['items']
                if ordered_assets != st.session_state['master_order']:
                    st.session_state['master_order'] = ordered_assets # ドラッグ結果を保存
            else:
                ordered_assets = st.session_state['master_order']
        except Exception as e:
            ordered_assets = selected_assets_base
            
        bg_mode = st.radio("背景色設定", ["明るい (白)", "暗い (黒)"], horizontal=True)
        color_pattern = st.radio("騰落カラー設定", ["日本式 (上昇:赤 / 下落:緑)", "欧米式 (上昇:緑 / 下落:赤)"], horizontal=True)

    # カラーコード定義
    is_dark = bg_mode == "暗い (黒)"
    theme_bg = "#0f172a" if is_dark else "#f8fafc"
    theme_card = "#1e293b" if is_dark else "#ffffff"
    theme_text = "#f1f5f9" if is_dark else "#1e293b"
    theme_border = "#334155" if is_dark else "#e2e8f0"
    theme_muted = "#94a3b8" if is_dark else "#64748b"

    # カスタムCSSインジェクション（全タブ統一プレミアムUI）
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+JP:wght@400;500;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', 'Noto Sans JP', sans-serif; }}

    div[data-testid="column"] {{ padding: 4px !important; }}

    /* ============================
       共通タブバーのスタイル
       ============================ */
    .stTabs [data-baseweb="tab-list"] {{ gap: 8px; }}
    .stTabs [data-baseweb="tab"] {{
        font-weight: 600;
        font-size: 0.95rem;
        padding: 10px 20px;
        border-radius: 8px 8px 0 0;
    }}
    .stTabs [aria-selected="true"] {{
        border-bottom: 3px solid #3B82F6 !important;
        color: #3B82F6 !important;
    }}

    /* ============================
       Tab1: マーケット — モダンカードデザイン
       ============================ */
    .m-tile {{
        background-color: {theme_card};
        border: 1px solid {theme_border};
        padding: 12px 14px 4px 14px;
        border-radius: 12px;
        margin-bottom: 6px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        transition: all 0.2s ease-in-out;
        position: relative;
        overflow: hidden;
    }}
    .m-tile:hover {{ 
        transform: translateY(-2px); 
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        border-color: {theme_muted};
        z-index: 10;
    }}
    .m-tile-accent {{
        position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
    }}
    .m-tile-inner {{ display: flex; justify-content: space-between; align-items: flex-end; width: 100%; }}
    .m-tile-left {{ text-align: left; }}
    .m-tile-right {{ text-align: right; display: flex; flex-direction: column; align-items: flex-end; }}
    .m-tile-name {{ font-size: 0.9rem; font-weight: 600; color: {theme_text}; margin-bottom: 4px; }}
    .m-tile-price {{ font-family: 'Inter', sans-serif; font-size: 1.35rem; font-weight: 700; color: {theme_text}; line-height: 1.1; margin-bottom: 4px; letter-spacing: -0.5px; }}
    .m-tile-badge {{ 
        font-family: 'Inter', sans-serif; font-size: 0.75rem; font-weight: 600; 
        padding: 2px 6px; border-radius: 6px; display: inline-block;
    }}

    /* ============================
       Tab2: ニュース — カード＆バッジ
       ============================ */
    .news-section-header {{
        font-size: 1.2rem;
        font-weight: 700;
        padding: 10px 16px;
        border-radius: 10px;
        margin-bottom: 12px;
        background: linear-gradient(135deg, #1E293B 0%, #334155 100%);
        color: #F8FAFC;
        letter-spacing: 0.5px;
    }}
    .news-card {{
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #3B82F6;
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 8px;
        transition: all 0.2s ease;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}
    .news-card:hover {{
        transform: translateX(4px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border-left-color: #2563EB;
    }}
    .news-card a {{
        color: #1E293B;
        text-decoration: none;
        font-weight: 600;
        font-size: 0.92rem;
        line-height: 1.5;
        display: block;
    }}
    .news-card a:hover {{ color: #3B82F6; }}
    .news-meta {{
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 6px;
        font-size: 0.78rem;
        color: #64748b;
    }}
    .news-time-badge {{
        background: #EFF6FF;
        color: #3B82F6;
        padding: 2px 8px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.72rem;
    }}
    .news-source {{
        color: #94A3B8;
        font-weight: 500;
    }}

    /* ============================
       Tab3: カレンダー — 凡例カード
       ============================ */
    .guide-box {{
        background: linear-gradient(135deg, #F8FAFC 0%, #EFF6FF 100%);
        border: 1px solid #CBD5E1;
        border-radius: 14px;
        padding: 20px 24px;
        margin-bottom: 16px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.04);
    }}
    .guide-title {{
        font-size: 1.0rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 10px;
        padding-bottom: 6px;
        border-bottom: 2px solid #3B82F6;
        display: inline-block;
    }}
    .guide-grid {{
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 8px;
    }}
    .guide-item {{
        background: #ffffff;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 0.85rem;
        color: #334155;
        transition: background 0.15s;
    }}
    .guide-item:hover {{ background: #F1F5F9; }}
    .guide-item b {{ color: #1E293B; }}

    /* ============================
       Tab4: FIRE — パネル・ボタン・レポート
       ============================ */
    .rev-panel {{
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        color: #F8FAFC;
        border-radius: 14px;
        padding: 20px;
        margin: 12px 0;
        box-shadow: 0 8px 16px rgba(0,0,0,0.15);
        border: 1px solid #334155;
    }}
    .rev-panel div[style*="border-bottom"] {{
        border-bottom-color: #475569 !important;
        font-size: 1.1rem;
        letter-spacing: 0.5px;
    }}

    .fire-report-card {{
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        transition: all 0.2s ease;
        position: relative;
        overflow: hidden;
    }}
    .fire-report-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 8px 15px rgba(0,0,0,0.1);
    }}
    .fire-report-card::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 4px;
    }}
    .fire-report-normal {{ background: #F0F9FF; }}
    .fire-report-normal::before {{ background: linear-gradient(90deg, #3B82F6, #60A5FA); }}
    .fire-report-bull {{ background: #F0FDF4; }}
    .fire-report-bull::before {{ background: linear-gradient(90deg, #10B981, #34D399); }}
    .fire-report-bear {{ background: #FEF2F2; }}
    .fire-report-bear::before {{ background: linear-gradient(90deg, #EF4444, #F87171); }}
    .fire-report-title {{ font-weight: 700; font-size: 1.0rem; margin-bottom: 8px; }}
    .fire-report-status {{ font-weight: 700; font-size: 0.95rem; color: #1E293B; margin-bottom: 4px; }}
    .fire-report-amount {{ font-weight: 600; font-size: 0.88rem; color: #475569; }}

    /* Streamlitボタンのプレミアムスタイル */
    .stButton > button {{
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
        color: #ffffff;
        border: none;
        border-radius: 10px;
        font-weight: 600;
        font-size: 0.95rem;
        padding: 10px 20px;
        transition: all 0.25s ease;
        box-shadow: 0 4px 6px rgba(59, 130, 246, 0.25);
    }}
    .stButton > button:hover {{
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        box-shadow: 0 6px 12px rgba(59, 130, 246, 0.35);
        transform: translateY(-1px);
    }}
    .stButton > button:active {{
        transform: translateY(0px);
        box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);
    }}

    /* 共通グラフ外枠 - Streamlitのコンテナ要素を直接ターゲット */
    div[data-testid="stVerticalBlock"] > div:has(div.stPlotlyChart),
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {{
        border: 1px solid {theme_border} !important;
        border-radius: 12px !important;
        padding: 16px !important;
        background-color: {theme_card} !important;
        margin-bottom: 20px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
    }}
    .stPlotlyChart {{
        border: none !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    st.subheader("🌎 グローバル・マーケット・ボード")
    
    # グリッドレイアウト
    if not ordered_assets:
        st.info("サイドバーから表示したい資産を選択してください。")
    else:
        # 4列のグリッド
        cols = st.columns(4)
        for idx, name in enumerate(ordered_assets):
            with cols[idx % 4]:
                render_market_tile(name, ASSET_MASTER[name])

# --- Tab 2: ニュース ---
with tabs[1]:
    st.subheader("📰 最新経済ニュース (自動更新)")
    n_c1, n_c2 = st.columns(2)
    with n_c1:
        st.markdown('<div class="news-section-header">🇯🇵 日本: 経済・産業・社会情勢</div>', unsafe_allow_html=True)
        jp_news = fetch_latest_news("JP")
        if jp_news:
            for n in jp_news:
                source_name = n.source.get('title', 'Google News')
                st.markdown(f'<div class="news-card"><a href="{n.link}" target="_blank">{n.title}</a><div class="news-meta"><span class="news-time-badge">⏱ {n.rel_time}</span><span class="news-source">{source_name}</span></div></div>', unsafe_allow_html=True)
        else: st.info("現在、表示できる最新ニュースはありません。")
    with n_c2:
        st.markdown('<div class="news-section-header">🇺🇸 米国: 経済・産業・社会情勢</div>', unsafe_allow_html=True)
        us_news = fetch_latest_news("US")
        if us_news:
            for n in us_news:
                source_name = n.source.get('title', 'Google News')
                st.markdown(f'<div class="news-card"><a href="{n.link}" target="_blank">{n.title}</a><div class="news-meta"><span class="news-time-badge">⏱ {n.rel_time}</span><span class="news-source">{source_name}</span></div></div>', unsafe_allow_html=True)
        else: st.info("現在、表示できる最新ニュースはありません。")

# --- Tab 4: カレンダー ---
with tabs[3]:
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

# --- Tab 6: FIREシミュレーター ---
with tabs[5]:
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
            st.markdown(f'<div class="rev-panel"><div style="font-weight:700; margin-bottom:8px; border-bottom:1px solid #475569; font-size:1.1rem;">最短FIRE可能年齢</div><div style="color:#10B981;">🚀 強気: <b>{res["強気"] if res["強気"] else "不可"}歳</b></div><div style="color:#3B82F6;">📊 通常: <b>{res["通常"] if res["通常"] else "不可"}歳</b></div><div style="color:#EF4444;">⚠️ 弱気: <b>{res["弱気"] if res["弱気"] else "不可"}歳</b></div></div>', unsafe_allow_html=True)
            if res['通常'] and st.button("通常結果を適用"): st.session_state['fire_age_val'] = res['通常']; st.rerun()

    with f_out:
        sim = FIRESimulator()
        all_res = sim.calculate({'currentAge': age, 'currentAssets': total_curr, 'nisaAssets': c_nisa, 'nisaLimitRemaining': nisa_rem, 'taxRate': tax_rate, 'monthlyInvestment': m_inv, 'expectedReturnPre': r_pre, 'expectedReturnPost': r_post, 'expectedReturnPreBull': r_pre + r_bull, 'expectedReturnPostBull': r_post + r_bull, 'expectedReturnPreBear': max(0, r_pre - r_bear), 'expectedReturnPostBear': max(0, r_post - r_bear), 'fireAge': f_age, 'livingExpense': l_exp, 'inflationRate': inf, 'pensionAmount': p_val, 'pensionAge': p_age, 'retirementAllowance': ret_al})
        fig = go.Figure()
        clrs = {"通常": "#3B82F6", "強気": "#10B981", "弱気": "#EF4444"}
        for n in show_scen:
            df_h = pd.DataFrame(all_res[n]['history'])
            fig.add_trace(go.Scatter(x=df_h['age'], y=df_h['totalAssets'], name=n, line=dict(color=clrs[n], width=3), customdata=df_h['age'], hovertemplate="%{customdata}歳<br>資産: %{y:,.0f} 万円<extra></extra>"))
        fig.update_layout(title="将来資産推移", xaxis_title="年齢", yaxis_title="資産額 (万円)", template="plotly_white", hovermode="x unified", xaxis=dict(hoverformat=".0f歳"))
        with st.container(border=True):
            st.plotly_chart(fig, use_container_width=True)
        
        # シェア用のサマリー作成
        normal_rep = all_res["通常"]
        status_msg = "✅100歳まで安泰" if not normal_rep['exhaustionAge'] else f"⚠️{normal_rep['exhaustionAge']}歳で枯渇"
        
        # 最短FIRE年齢が計算されているかどうかで文面を変える
        rev = st.session_state.get('rev_results')
        if rev and rev.get('通常'):
            fire_info = f"📊 最短FIRE年齢: {rev['通常']}歳"
        else:
            fire_info = f"📅 設定FIRE年齢: {f_age}歳"

        share_text = f"【FIREシミュレーション結果】🚀\n{fire_info}\n📋 診断: {status_msg}\n💰 100歳時予想資産: {normal_rep['finalAssets']:,.0f}万円\n🔥 #資産形成の羅針盤 #FIRE"
        st.markdown(get_share_button_html(share_text), unsafe_allow_html=True)
        
        st.subheader("📋 シミュレーション診断レポート")
        rep_cols = st.columns(3)
        scen_css = {"通常": "fire-report-normal", "強気": "fire-report-bull", "弱気": "fire-report-bear"}
        for idx, n in enumerate(show_scen):
            r = all_res[n]
            css_class = scen_css.get(n, "fire-report-normal")
            status_text = "✅ 100歳まで安泰" if not r['exhaustionAge'] else f"⚠️ {r['exhaustionAge']}歳で枯渇"
            with rep_cols[idx]:
                st.markdown(f'<div class="fire-report-card {css_class}"><div class="fire-report-title" style="color:{clrs[n]};">{n}シナリオ</div><div class="fire-report-status">{status_text}</div><div class="fire-report-amount">100歳時: {r["finalAssets"]:,.0f}万円</div></div>', unsafe_allow_html=True)

# --- Tab 5: 不労所得リアルタイムメーター ---
with tabs[4]:
    st.subheader("⏱️ 不労所得リアルタイムメーター")
    st.caption("あなたの資産が「今この瞬間も」いくら稼いでいるかをリアルタイムで可視化します。")
    
    pm_c1, pm_c2 = st.columns(2)
    with pm_c1:
        pm_assets = st.number_input("保有資産額 (万円)", 0.0, 1000000.0, 1000.0, step=100.0, key="pm_assets")
    with pm_c2:
        pm_rate = st.number_input("想定年利回り (%)", 0.0, 30.0, 5.0, step=0.5, key="pm_rate")
    
    # 計算
    annual_income = pm_assets * pm_rate / 100  # 万円/年
    daily_income = annual_income / 365
    hourly_income = daily_income / 24
    per_minute = hourly_income / 60
    per_second = per_minute / 60
    per_second_yen = per_second * 10000  # 円換算
    daily_income_yen = daily_income * 10000
    annual_income_yen = annual_income * 10000
    
    # JavaScriptリアルタイムカウンター（スマホ対応: グリッドレイアウト）
    counter_html = f"""
    <div style="background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); border-radius: 16px; padding: 24px 16px; text-align: center; margin: 16px 0; box-shadow: 0 8px 24px rgba(0,0,0,0.2); border: 1px solid #334155;">
        <div style="color: #94A3B8; font-size: 0.95rem; font-weight: 600; margin-bottom: 8px; letter-spacing: 1px;">💰 あなたの資産が今この瞬間も稼いでいます</div>
        <div style="color: #F8FAFC; font-family: 'Inter', sans-serif; font-size: 2.5rem; font-weight: 700; letter-spacing: -1px;" id="pm-counter">¥ 0.0000</div>
        <div style="color: #64748B; font-size: 0.85rem; margin-top: 4px;">（本日の累計不労所得）</div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 8px; margin-top: 16px; padding: 0 8px;">
            <div style="background: rgba(59,130,246,0.1); border-radius: 8px; padding: 8px 6px;"><div style="color:#3B82F6; font-weight:700; font-size:0.75rem;">⏱ 1秒</div><div style="color:#F8FAFC; font-size:0.85rem; font-weight:600;">¥{per_second_yen:.4f}</div></div>
            <div style="background: rgba(59,130,246,0.1); border-radius: 8px; padding: 8px 6px;"><div style="color:#3B82F6; font-weight:700; font-size:0.75rem;">⏱ 1分</div><div style="color:#F8FAFC; font-size:0.85rem; font-weight:600;">¥{per_minute * 10000:.2f}</div></div>
            <div style="background: rgba(59,130,246,0.1); border-radius: 8px; padding: 8px 6px;"><div style="color:#3B82F6; font-weight:700; font-size:0.75rem;">⏱ 1時間</div><div style="color:#F8FAFC; font-size:0.85rem; font-weight:600;">¥{hourly_income * 10000:,.1f}</div></div>
            <div style="background: rgba(59,130,246,0.1); border-radius: 8px; padding: 8px 6px;"><div style="color:#3B82F6; font-weight:700; font-size:0.75rem;">⏱ 1日</div><div style="color:#F8FAFC; font-size:0.85rem; font-weight:600;">¥{daily_income_yen:,.0f}</div></div>
            <div style="background: rgba(16,185,129,0.15); border-radius: 8px; padding: 8px 6px;"><div style="color:#10B981; font-weight:700; font-size:0.75rem;">⏱ 1年</div><div style="color:#F8FAFC; font-size:0.85rem; font-weight:600;">¥{annual_income_yen:,.0f}</div></div>
        </div>
    </div>
    <script>
        var perSecond = {per_second_yen};
        var total = 0;
        var counterEl = document.getElementById('pm-counter');
        setInterval(function() {{
            total += perSecond;
            counterEl.innerText = '¥ ' + total.toLocaleString('ja-JP', {{minimumFractionDigits: 4, maximumFractionDigits: 4}});
        }}, 1000);
    </script>
    """
    components.html(counter_html, height=280)
    
    # シェアボタンをメーター直下に配置
    st.markdown(get_share_button_html(f"【不労所得メーター】💰 私の資産は1日に「{daily_income_yen:,.0f}円」、1年で「{annual_income_yen:,.0f}円」稼いでいます！ 🗓️✨ #配当金 #資産形成の羅針盤"), unsafe_allow_html=True)
    
    # 時給換算カード（components.htmlでCSS Grid描画: PC=3列, スマホ=1列/金額昇順）
    st.markdown('<h4 style="margin-bottom: -15px;">💡 生活費との比較（あなたの不労所得で何が賄える？）</h4>', unsafe_allow_html=True)
    life_items = [
        {"icon": "☕", "name": "コーヒー1杯", "cost": 500, "mobile_order": 1},
        {"icon": "🍽️", "name": "外食ランチ", "cost": 1000, "mobile_order": 2},
        {"icon": "📱", "name": "スマホ代 (月)", "cost": 8000, "mobile_order": 3},
        {"icon": "💡", "name": "電気代 (月)", "cost": 12000, "mobile_order": 4},
        {"icon": "🏠", "name": "家賃 (月)", "cost": 150000, "mobile_order": 5},
        {"icon": "✈️", "name": "海外旅行", "cost": 500000, "mobile_order": 6},
    ]
    cards_html = ""
    for item in life_items:
        if daily_income_yen > 0:
            hours_needed = item["cost"] / (hourly_income * 10000)
            if hours_needed < 1:
                time_str = f"{hours_needed * 60:.0f}分"
            elif hours_needed < 24:
                time_str = f"{hours_needed:.1f}時間"
            else:
                time_str = f"{hours_needed / 24:.1f}日"
        else:
            time_str = "∞"
        cards_html += f'''<div class="li-card" style="order:{item['mobile_order']};">
            <div style="font-size:1.5rem;">{item["icon"]}</div>
            <div style="font-weight:700; font-size:1.0rem; color:#1E293B; margin-bottom:2px;">{item["name"]}</div>
            <div style="color:#64748B; font-size:0.82rem;">¥{item["cost"]:,}</div>
            <div style="font-weight:700; font-size:0.95rem; color:#3B82F6; margin-top:4px;">不労所得で{time_str}</div>
        </div>'''
    
    life_grid_html = f"""
    <style>
        .li-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; padding: 4px; }}
        .li-card {{ background: #F0F9FF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 16px; text-align: center;
                    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); transition: all 0.2s ease; position: relative; overflow: hidden; }}
        .li-card:hover {{ transform: translateY(-2px); box-shadow: 0 8px 15px rgba(0,0,0,0.1); }}
        .li-card::before {{ content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, #3B82F6, #60A5FA); }}
        @media (max-width: 768px) {{
            .li-grid {{ grid-template-columns: 1fr !important; }}
        }}
    </style>
    <div class="li-grid">{cards_html}</div>
    """
    st.markdown(life_grid_html, unsafe_allow_html=True)

# --- Tab 3: 日本版 恐怖＆強欲メーター (CNN Fear & Greed Index 準拠) ---
with tabs[2]:
    st.subheader("🎰 日本版 Fear & Greed Index")
    st.caption("CNN Fear & Greed Index に準拠した7つの市場指標を均等加重（各1/7）で統合し、投資家心理を0〜100で評価します。")
    
    @st.cache_data(ttl=600)
    def calc_fear_greed():
        w = 1.0 / 7.0  # CNN準拠: 均等加重
        scores = {}
        
        # ① 株価モメンタム: 日経平均 vs 125日移動平均 (CNN: S&P500 vs 125-day MA)
        try:
            nk = yf.Ticker("^N225").history(period="160d")
            ma125 = nk['Close'].rolling(125).mean().iloc[-1]
            curr = nk['Close'].iloc[-1]
            pct_above = ((curr - ma125) / ma125) * 100
            scores['MOMENTUM'] = {'value': f"{pct_above:+.2f}%", 'score': max(0, min(100, 50 + pct_above * 4)), 'weight': w}
        except:
            scores['MOMENTUM'] = {'value': 'N/A', 'score': 50, 'weight': w}
        
        # ② 株価の強さ: 大型株 vs 小型株の相対パフォーマンス20日 (CNN: 52週新高値/新安値比率の代替)
        try:
            topix = yf.Ticker("1306.T").history(period="30d")
            mothers = yf.Ticker("2516.T").history(period="30d")
            topix_ret = (topix['Close'].iloc[-1] / topix['Close'].iloc[-20] - 1) * 100
            mothers_ret = (mothers['Close'].iloc[-1] / mothers['Close'].iloc[-20] - 1) * 100
            breadth = topix_ret - mothers_ret
            scores['STRENGTH'] = {'value': f"{breadth:+.2f}%", 'score': max(0, min(100, 50 + breadth * 5)), 'weight': w}
        except:
            scores['STRENGTH'] = {'value': 'N/A', 'score': 50, 'weight': w}
        
        # ③ 市場の広がり: 日経ETF出来高 vs 50日平均出来高 (CNN: McClellan Volume代替)
        try:
            nk_vol = yf.Ticker("1321.T").history(period="70d")
            avg_vol = nk_vol['Volume'].rolling(50).mean().iloc[-1]
            curr_vol = nk_vol['Volume'].iloc[-5:].mean()
            vol_ratio = (curr_vol / avg_vol - 1) * 100 if avg_vol > 0 else 0
            scores['BREADTH'] = {'value': f"{vol_ratio:+.1f}%", 'score': max(0, min(100, 50 + vol_ratio * 0.5)), 'weight': w}
        except:
            scores['BREADTH'] = {'value': 'N/A', 'score': 50, 'weight': w}
        
        # ④ プット/コール比率代替: VIX短期トレンド 5日MA vs 20日MA (CNN: Put/Call Ratio代替)
        try:
            vix_pc = yf.Ticker("^VIX").history(period="30d")
            vix_ma5 = vix_pc['Close'].rolling(5).mean().iloc[-1]
            vix_ma20 = vix_pc['Close'].rolling(20).mean().iloc[-1]
            vix_trend = ((vix_ma5 - vix_ma20) / vix_ma20) * 100
            scores['PUTCALL'] = {'value': f"{vix_trend:+.2f}%", 'score': max(0, min(100, 50 - vix_trend * 3)), 'weight': w}
        except:
            scores['PUTCALL'] = {'value': 'N/A', 'score': 50, 'weight': w}
        
        # ⑤ 市場のボラティリティ: VIX vs 50日移動平均 (CNN: VIX vs 50-day MA)
        try:
            vix_data = yf.Ticker("^VIX").history(period="70d")
            vix_curr = vix_data['Close'].iloc[-1]
            vix_ma50 = vix_data['Close'].rolling(50).mean().iloc[-1]
            vix_diff = ((vix_curr - vix_ma50) / vix_ma50) * 100
            scores['VOLATILITY'] = {'value': f"VIX {vix_curr:.1f}", 'score': max(0, min(100, 50 - vix_diff * 2)), 'weight': w}
        except:
            scores['VOLATILITY'] = {'value': 'N/A', 'score': 50, 'weight': w}
        
        # ⑥ 安全資産への逃避: 株式 vs 債券の20日リターン比較 (CNN: Stock vs Bond returns)
        try:
            stk = yf.Ticker("^N225").history(period="30d")
            bnd = yf.Ticker("TLT").history(period="30d")
            stk_ret = (stk['Close'].iloc[-1] / stk['Close'].iloc[-20] - 1) * 100
            bnd_ret = (bnd['Close'].iloc[-1] / bnd['Close'].iloc[-20] - 1) * 100
            spread = stk_ret - bnd_ret
            scores['SAFEHAVEN'] = {'value': f"{spread:+.2f}%", 'score': max(0, min(100, 50 + spread * 4)), 'weight': w}
        except:
            scores['SAFEHAVEN'] = {'value': 'N/A', 'score': 50, 'weight': w}
        
        # ⑦ ジャンク債需要: HYG vs LQD の20日リターン比較 (CNN: Junk Bond Demand)
        try:
            hyg = yf.Ticker("HYG").history(period="30d")
            lqd = yf.Ticker("LQD").history(period="30d")
            hyg_ret = (hyg['Close'].iloc[-1] / hyg['Close'].iloc[-20] - 1) * 100
            lqd_ret = (lqd['Close'].iloc[-1] / lqd['Close'].iloc[-20] - 1) * 100
            junk_spread = hyg_ret - lqd_ret
            scores['JUNKBOND'] = {'value': f"{junk_spread:+.2f}%", 'score': max(0, min(100, 50 + junk_spread * 10)), 'weight': w}
        except:
            scores['JUNKBOND'] = {'value': 'N/A', 'score': 50, 'weight': w}
        
        # 均等加重平均スコア
        total_score = sum(s['score'] * s['weight'] for s in scores.values())
        return round(total_score, 1), scores

    @st.cache_data(ttl=3600)
    def calc_fear_greed_history():
        # 必要な期間: 1年(250日) + MA125用バッファ = 約400日
        period = "500d"
        try:
            # 1. データの取得
            def get_safe_data(ticker, p="500d"):
                df = yf.Ticker(ticker).history(period=p)
                if df.empty: return None
                df.index = pd.to_datetime(df.index).tz_localize(None)
                return df

            nk = get_safe_data("^N225")
            tp_stable = get_safe_data("1348.T") # 分割の影響がないETFを採用
            mo_etf = get_safe_data("2516.T")
            nk_vol = get_safe_data("1321.T")
            vix = get_safe_data("^VIX")
            tlt = get_safe_data("TLT")
            hyg = get_safe_data("HYG")
            lqd = get_safe_data("LQD")

            # 必須データが一つでも欠けていたら中断
            if any(x is None for x in [nk, tp_stable, mo_etf, nk_vol, vix, tlt, hyg, lqd]):
                return None

            # 共通のインデックスで揃える (日本営業日ベース)
            idx = nk.index
            def align(df):
                return df.reindex(idx).ffill()

            # ① モメンタム (Nikkei vs 125MA)
            ma125 = nk['Close'].rolling(125).mean()
            mom_pct = ((nk['Close'] - ma125) / ma125) * 100
            mom_score = (50 + mom_pct * 4).clip(0, 100)
            
            # ② 株価の強さ (Large vs Small 20d return spread)
            tp_stable_c = align(tp_stable['Close'])
            mo_etf_c = align(mo_etf['Close'])
            tp_ret20 = tp_stable_c.pct_change(20) * 100
            mo_ret20 = mo_etf_c.pct_change(20) * 100
            str_spread = tp_ret20 - mo_ret20
            str_score = (50 + str_spread * 5).clip(0, 100)
            
            # ③ 市場の広がり (Vol vs 50d Avg Vol)
            nk_vol_v = align(nk_vol['Volume'])
            vol5d = nk_vol_v.rolling(5).mean()
            vol50d = nk_vol_v.rolling(50).mean()
            vol_ratio = ((vol5d / vol50d) - 1) * 100
            brd_score = (50 + vol_ratio * 0.5).clip(0, 100)
            
            # ④ P/C比率代替 (VIX 5MA vs 20MA)
            vix_c = align(vix['Close'])
            vix5ma = vix_c.rolling(5).mean()
            vix20ma = vix_c.rolling(20).mean()
            vix_trend = ((vix5ma - vix20ma) / vix20ma) * 100
            pc_score = (50 - vix_trend * 3).clip(0, 100)
            
            # ⑤ ボラティリティ (VIX vs 50MA)
            vix50ma = vix_c.rolling(50).mean()
            vix_diff = ((vix_c - vix50ma) / vix50ma) * 100
            volat_score = (50 - vix_diff * 2).clip(0, 100)
            
            # ⑥ 安全資産逃避 (Equity vs Bond 20d return)
            tlt_c = align(tlt['Close'])
            tlt_ret20 = tlt_c.pct_change(20) * 100
            safe_spread = nk['Close'].pct_change(20)*100 - tlt_ret20
            safe_score = (50 + safe_spread * 4).clip(0, 100)
            
            # ⑦ ジャンク債需要 (HYG vs LQD 20d return)
            hyg_c = align(hyg['Close'])
            lqd_c = align(lqd['Close'])
            hyg_ret20 = hyg_c.pct_change(20) * 100
            lqd_ret20 = lqd_c.pct_change(20) * 100
            junk_spread = hyg_ret20 - lqd_ret20
            junk_score = (50 + junk_spread * 10).clip(0, 100)
            
            # 3. 総合スコアの集計
            df_hist = pd.DataFrame({
                'FG_Index': (mom_score + str_score + brd_score + pc_score + volat_score + safe_score + junk_score) / 7.0,
                'Nikkei225': nk['Close'],
                'TOPIX': tp_stable_c
            }).dropna()
            
            if df_hist.empty:
                return None

            # 直近1年分を抽出
            one_year_ago = df_hist.index.max() - pd.Timedelta(days=365)
            df_hist = df_hist[df_hist.index >= one_year_ago]
            
            return df_hist
        except Exception as e:
            st.error(f"時系列データの計算中にエラーが発生しました: {e}")
            return None
        except Exception as e:
            st.error(f"時系列データの計算中にエラーが発生しました: {e}")
            return None

    fg_score, fg_details = calc_fear_greed()
    
    # ラベル判定
    if fg_score <= 20: fg_label, fg_emoji, fg_color = "極度の恐怖", "😱", "#991B1B"
    elif fg_score <= 40: fg_label, fg_emoji, fg_color = "恐怖", "😟", "#EF4444"
    elif fg_score <= 60: fg_label, fg_emoji, fg_color = "中立", "😐", "#64748B"
    elif fg_score <= 80: fg_label, fg_emoji, fg_color = "強欲", "😊", "#10B981"
    else: fg_label, fg_emoji, fg_color = "極度の強欲", "🤑", "#065F46"
    
    # ゲージメーター (Plotly)
    fig_fg = go.Figure(go.Indicator(
        mode="gauge+number",
        value=fg_score,
        number={'suffix': '', 'font': {'size': 48, 'color': fg_color, 'family': 'Inter'}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 2, 'tickcolor': '#94A3B8'},
            'bar': {'color': fg_color, 'thickness': 0.3},
            'bgcolor': '#F1F5F9',
            'borderwidth': 0,
            'steps': [
                {'range': [0, 20], 'color': '#FEE2E2'},
                {'range': [20, 40], 'color': '#FECACA'},
                {'range': [40, 60], 'color': '#F1F5F9'},
                {'range': [60, 80], 'color': '#D1FAE5'},
                {'range': [80, 100], 'color': '#A7F3D0'},
            ],
            'threshold': {'line': {'color': fg_color, 'width': 4}, 'thickness': 0.8, 'value': fg_score}
        }
    ))
    fig_fg.update_layout(height=280, margin=dict(l=30, r=30, t=40, b=10), paper_bgcolor='rgba(0,0,0,0)', font={'family': 'Inter, Noto Sans JP'})
    
    col1, col2 = st.columns([1, 2])
    with col1:
        with st.container(border=True):
            st.plotly_chart(fig_fg, use_container_width=True)
            st.markdown(f'<div style="text-align:center; font-size:1.5rem; font-weight:700; color:{fg_color}; margin-top:-20px; margin-bottom:10px;">{fg_emoji} {fg_label}</div>', unsafe_allow_html=True)
    
    with col2:
        df_hist = calc_fear_greed_history()
        if df_hist is not None:
            # 正規化 (騰落率ベース)
            df_norm = df_hist.copy()
            df_norm['Nikkei225'] = (df_norm['Nikkei225'] / df_norm['Nikkei225'].iloc[0]) * 100
            df_norm['TOPIX'] = (df_norm['TOPIX'] / df_norm['TOPIX'].iloc[0]) * 100
            
            from plotly.subplots import make_subplots
            fig_chart = make_subplots(specs=[[{"secondary_y": True}]])
            
            # 株価推移 (左軸)
            fig_chart.add_trace(go.Scatter(x=df_norm.index, y=df_norm['Nikkei225'], name="日経平均 (%)", line=dict(color='#3B82F6', width=2)), secondary_y=False)
            fig_chart.add_trace(go.Scatter(x=df_norm.index, y=df_norm['TOPIX'], name="TOPIX (%)", line=dict(color='#94A3B8', width=1.5, dash='dot')), secondary_y=False)
            
            # Fear & Greed (右軸)
            fig_chart.add_trace(go.Scatter(
                x=df_norm.index, y=df_norm['FG_Index'], name="Fear & Greed",
                fill='tozeroy', fillcolor='rgba(148, 163, 184, 0.1)',
                line=dict(color='#F59E0B', width=2.5)
            ), secondary_y=True)
            
            # カラーゾーン設定
            fig_chart.add_hrect(y0=0, y1=20, fillcolor="red", opacity=0.05, line_width=0, secondary_y=True)
            fig_chart.add_hrect(y0=80, y1=100, fillcolor="green", opacity=0.05, line_width=0, secondary_y=True)

            fig_chart.update_layout(
                title_text="📈 センチメント vs 株価推移 (直近1年)",
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                height=320,
                margin=dict(l=0, r=0, t=40, b=0),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
            )
            fig_chart.update_xaxes(showgrid=False)
            fig_chart.update_yaxes(title_text="株価騰落率 (%)", secondary_y=False, showgrid=True, gridcolor='#E2E8F0')
            fig_chart.update_yaxes(title_text="F&G Index", secondary_y=True, range=[0, 100], showgrid=False)
            
            with st.container(border=True):
                st.plotly_chart(fig_chart, use_container_width=True)

    # 構成指標ミニカード（7指標・CNN準拠）
    st.markdown("#### 📊 構成指標の内訳（CNN準拠・各 14.3% の均等加重）")
    indicator_names = {
        'MOMENTUM': '① 株価モメンタム', 'STRENGTH': '② 株価の強さ', 'BREADTH': '③ 市場の広がり',
        'PUTCALL': '④ P/C比率代替', 'VOLATILITY': '⑤ ボラティリティ', 'SAFEHAVEN': '⑥ 安全資産逃避', 'JUNKBOND': '⑦ ジャンク債需要'
    }
    indicator_desc = {
        'MOMENTUM': '日経 vs 125日MA', 'STRENGTH': '大型株 vs 小型株', 'BREADTH': '出来高 vs 50日平均',
        'PUTCALL': 'VIX 5日MA vs 20日MA', 'VOLATILITY': 'VIX vs 50日MA', 'SAFEHAVEN': '株式 vs 債券リターン', 'JUNKBOND': 'HYG vs LQD リターン'
    }
    fg_cols_top = st.columns(4)
    fg_cols_bot = st.columns([1,1,1,1])
    fg_keys = list(fg_details.keys())
    for idx, key in enumerate(fg_keys):
        data = fg_details[key]
        col = fg_cols_top[idx] if idx < 4 else fg_cols_bot[idx - 4]
        with col:
            sc = data['score']
            sc_color = "#EF4444" if sc < 40 else ("#10B981" if sc > 60 else "#64748B")
            st.markdown(f'''<div class="fire-report-card fire-report-normal" style="padding:12px; margin-bottom:8px;">
                <div style="font-size:0.75rem; font-weight:700; color:#1E293B; margin-bottom:4px;">{indicator_names[key]}</div>
                <div style="font-size:1.3rem; font-weight:700; color:{sc_color};">{sc:.0f}</div>
                <div style="font-size:0.7rem; color:#64748B;">{data["value"]}</div>
                <div style="font-size:0.62rem; color:#94A3B8; margin-top:2px;">{indicator_desc[key]}</div>
            </div>''', unsafe_allow_html=True)
    
    # シェアボタン
    st.markdown(get_share_button_html(f"【日本版 Fear & Greed Index】📉📈 現在の市場心理は「{fg_label}」({fg_score})です！投資家は今、{fg_label}に傾いています。{fg_emoji} #資産形成の羅針盤 #投資家心理"), unsafe_allow_html=True)

# --- Tab 7: 暴落プレイバック ストレステスト ---
with tabs[6]:
    st.subheader("🌊 暴落プレイバック ストレステスト")
    st.caption("過去の歴史的暴落が「今」起きたら、あなたの資産はどうなるかをシミュレーションします。")
    
    # 暴落パターン定義
    CRASH_PATTERNS = {
        "リーマンショック (2008)": {"max_drop": -56.8, "months_to_bottom": 17, "months_to_recover": 65, "desc": "米国サブプライムローン危機。世界同時株安。", "curve": [0,-8,-15,-25,-32,-38,-42,-45,-48,-50,-52,-54,-55.5,-56,-56.5,-56.8,-56,-52,-48,-44,-40,-36,-32,-28,-24,-20,-16,-12,-8,-4,0]},
        "コロナショック (2020)": {"max_drop": -33.9, "months_to_bottom": 1, "months_to_recover": 5, "desc": "COVID-19パンデミックによる急落。V字回復。", "curve": [0,-12,-25,-33.9,-28,-20,-12,-5,0]},
        "ITバブル崩壊 (2000)": {"max_drop": -78.4, "months_to_bottom": 30, "months_to_recover": 180, "desc": "ドットコムバブルの崩壊。NASDAQが約80%下落。", "curve": [0,-5,-10,-18,-25,-30,-38,-45,-50,-55,-60,-65,-68,-72,-75,-77,-78,-78.4,-76,-72,-68,-64,-60,-55,-50,-45,-40,-35,-30,-25,-20,-15,-10,-5,0]},
        "ブラックマンデー (1987)": {"max_drop": -22.6, "months_to_bottom": 0.1, "months_to_recover": 24, "desc": "1日でNYダウが22.6%下落。", "curve": [0,-22.6,-20,-18,-15,-12,-10,-8,-6,-4,-2,0]},
        "日経バブル崩壊 (1990)": {"max_drop": -63.2, "months_to_bottom": 32, "months_to_recover": 408, "desc": "日経平均39,000円→14,000円台。回復に34年。", "curve": [0,-5,-10,-15,-20,-28,-35,-40,-45,-48,-50,-53,-55,-57,-59,-60,-61,-62,-63,-63.2,-62,-60,-58,-55,-52,-50,-48,-45,-42,-40,-38,-35,-30,-25,-20,-15,-10,-5,0]},
    }
    
    # ポートフォリオ入力
    st.markdown("#### 💼 ポートフォリオ入力")
    crash_assets = {
        "日本株（日経平均連動）": 1.0,
        "米国株（S&P500連動）": 1.0,
        "全世界株式（オルカン）": 0.9,
        "先進国債券": 0.2,
        "金（ゴールド）": -0.3,
        "現金・預金": 0.0,
    }
    
    ca_cols = st.columns(3)
    portfolio = {}
    for idx, (asset_name, _) in enumerate(crash_assets.items()):
        with ca_cols[idx % 3]:
            val = st.number_input(f"{asset_name} (万円)", 0.0, 100000.0, 0.0, step=50.0, key=f"crash_{idx}")
            if val > 0:
                portfolio[asset_name] = val
    
    total_portfolio = sum(portfolio.values())
    if total_portfolio > 0:
        st.markdown(f"**ポートフォリオ合計: {total_portfolio:,.0f} 万円**")
    
    # 暴落シナリオ選択
    st.markdown("#### 💥 暴落シナリオ選択")
    selected_crash = st.radio("シナリオを選んでください", list(CRASH_PATTERNS.keys()), horizontal=True)
    crash = CRASH_PATTERNS[selected_crash]
    
    st.info(f"📖 {crash['desc']}")
    
    # シミュレーション実行ボタン → 結果をsession_stateに保存
    if total_portfolio > 0 and st.button("🔥 暴落シミュレーション実行", use_container_width=True, key="crash_btn"):
        curve = crash['curve']
        total_values = []
        for step_pct in curve:
            step_total = 0
            for asset_name, amount in portfolio.items():
                correlation = crash_assets.get(asset_name, 1.0)
                adjusted_drop = step_pct * correlation
                step_total += amount * (1 + adjusted_drop / 100)
            total_values.append(step_total)
        st.session_state['crash_result'] = {
            'total_values': total_values, 'total_portfolio': total_portfolio,
            'selected_crash': selected_crash, 'crash': crash, 'curve': curve
        }
    elif total_portfolio == 0:
        st.warning("上の入力欄にポートフォリオの金額を入力してください。")
    
    # 結果表示（session_stateから読み出し → 数値変更でも消えない）
    if 'crash_result' in st.session_state:
        cr = st.session_state['crash_result']
        total_values = cr['total_values']
        tp = cr['total_portfolio']
        timeline_labels = [f"月{i}" for i in range(len(cr['curve']))]
        
        fig_crash = go.Figure()
        fig_crash.add_trace(go.Scatter(
            x=timeline_labels, y=[tp] * len(cr['curve']),
            mode='lines', line=dict(color='rgba(0,0,0,0)', width=0), hoverinfo='skip'
        ))
        fig_crash.add_trace(go.Scatter(
            x=timeline_labels, y=total_values,
            mode='lines', fill='tonexty',
            line=dict(color='#EF4444', width=3),
            fillcolor='rgba(239, 68, 68, 0.15)',
            name='資産推移',
            hovertemplate='%{x}<br>資産: %{y:,.0f}万円<extra></extra>'
        ))
        fig_crash.add_hline(y=tp, line_dash="dash", line_color="#3B82F6", line_width=2, annotation_text="現在の資産額")
        
        min_val = min(total_values)
        fig_crash.update_layout(
            title=f"📉 {cr['selected_crash']} シミュレーション結果",
            xaxis_title="経過期間", yaxis_title="資産額 (万円)",
            template="plotly_white", showlegend=False, height=400
        )
        with st.container(border=True):
            st.plotly_chart(fig_crash, use_container_width=True)
        
        max_loss = tp - min_val
        max_loss_pct = (max_loss / tp) * 100 if tp > 0 else 0
        
        sum_cols = st.columns(3)
        with sum_cols[0]:
            st.markdown(f'''<div class="fire-report-card fire-report-bear">
                <div class="fire-report-title" style="color:#EF4444;">📉 最大下落額</div>
                <div class="fire-report-status">-{max_loss:,.0f} 万円</div>
                <div class="fire-report-amount">(-{max_loss_pct:.1f}%)</div>
            </div>''', unsafe_allow_html=True)
        with sum_cols[1]:
            st.markdown(f'''<div class="fire-report-card fire-report-normal">
                <div class="fire-report-title" style="color:#3B82F6;">📅 底打ちまで</div>
                <div class="fire-report-status">約{cr['crash']['months_to_bottom']}ヶ月</div>
                <div class="fire-report-amount">最安値: {min_val:,.0f}万円</div>
            </div>''', unsafe_allow_html=True)
        with sum_cols[2]:
            st.markdown(f'''<div class="fire-report-card fire-report-bull">
                <div class="fire-report-title" style="color:#10B981;">📈 回復まで</div>
                <div class="fire-report-status">約{cr['crash']['months_to_recover']}ヶ月</div>
                <div class="fire-report-amount">({cr['crash']['months_to_recover'] / 12:.1f}年)</div>
            </div>''', unsafe_allow_html=True)
        
        # 追加投資シミュレーション（ボタンの外なので数値変更で即再計算される）
        st.markdown("---")
        st.markdown("#### 💡 もし底値で追加投資していたら？")
        add_inv = st.number_input("底値での追加投資額 (万円)", 0.0, 100000.0, 100.0, step=50.0, key="add_inv")
        if add_inv > 0:
            recovery_gain = add_inv * (100 / (100 + cr['crash']['max_drop'])) - add_inv
            st.success(f"底値で **{add_inv:,.0f}万円** を追加投資した場合、回復時点で **+{recovery_gain:,.0f}万円** の利益が見込めます（元本回復ベース）。")
        
# --- 下部固定広告（オーバーレイ） ---
# --- 下部固定広告（オーバーレイ） ---
def render_footer_ad():
    # 広告リストをすべて読み込む
    import json
    try:
        df_ads = pd.read_csv('ads_list.csv')
        ads_json = json.dumps(df_ads['html'].dropna().tolist())
    except:
        ads_json = json.dumps(['<div style="color:#64748B; font-size:12px;">Wealth Compass Ad</div>'])

    # レスポンシブな底上げ用CSS
    st.markdown("""
        <style>
        /* PC用（デフォルト） */
        .stApp {{ margin-bottom: 180px; }}
        
        /* スマホ用（幅768px未満） */
        @media (max-width: 768px) {{
            .stApp {{ margin-bottom: 115px; }}
        }}
        </style>
    """, unsafe_allow_html=True)

    # 回転ロジックを含むHTML/JS（レスポンシブ対応）
    footer_html = f"""
    <div id="footer-ad-root" style="
        position: fixed;
        bottom: 0; /* 0に修正（外側のiframeで浮かせるため） */
        left: 0;
        width: 100%;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(8px);
        z-index: 999999;
        display: flex;
        justify-content: center;
        align-items: center; /* 中央寄せに戻す */
        border-top: 1px solid #e2e8f0;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
    ">
        <style>
            /* PCサイズ */
            #footer-ad-root {{ height: 125px; }}
            #footer-ad-content img, #footer-ad-content iframe {{
                max-width: 100% !important;
                height: auto !important;
                max-height: 120px !important;
                object-fit: contain;
            }}
            /* スマホサイズ */
            @media (max-width: 768px) {{
                #footer-ad-root {{ height: 60px; }}
                #footer-ad-content img, #footer-ad-content iframe {{
                    max-height: 58px !important;
                }}
            }}
        </style>
        <div id="footer-ad-content" style="display:flex; justify-content:center; align-items:center; width:100%; height:100%; padding: 0 10px; overflow: hidden;">
            <!-- 広告挿入エリア -->
        </div>
    </div>
    <script>
        (function() {{
            const ads = {ads_json};
            const contentDiv = document.getElementById('footer-ad-content');
            
            function rotateAd() {{
                if (ads.length === 0) return;
                const randomAd = ads[Math.floor(Math.random() * ads.length)];
                contentDiv.innerHTML = randomAd;
                
                Array.from(contentDiv.querySelectorAll("script")).forEach(oldScript => {{
                    const newScript = document.createElement("script");
                    Array.from(oldScript.attributes).forEach(attr => newScript.setAttribute(attr.name, attr.value));
                    newScript.appendChild(document.createTextNode(oldScript.innerHTML));
                    oldScript.parentNode.replaceChild(newScript, oldScript);
                }});
            }}

            rotateAd(); 
            setInterval(rotateAd, 10000); 

            try {{
                window.parent.document.addEventListener('click', rotateAd);
            }} catch(e) {{
                document.addEventListener('click', rotateAd);
            }}

            // レスポンシブな高さ制御
            try {{
                const frame = window.frameElement;
                if (frame) {{
                    const updateSize = () => {{
                        const isMobile = window.innerWidth < 768;
                        const h = isMobile ? 60 : 125;
                        frame.style.position = 'fixed';
                        frame.style.bottom = '50px'; 
                        frame.style.left = '0';
                        frame.style.width = '100%';
                        frame.style.height = h + 'px';
                        frame.style.zIndex = '999999';
                        frame.style.pointerEvents = 'none';
                    }};
                    updateSize();
                    window.addEventListener('resize', updateSize);
                }}
                document.getElementById('footer-ad-root').style.pointerEvents = 'auto';
            }} catch (e) {{ console.log(e); }}
        }})();
    </script>
    """
    # Python側のheightは最大値に設定し、JS側で縮小を制御
    components.html(footer_html, height=125)

render_footer_ad()
