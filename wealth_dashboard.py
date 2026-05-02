import streamlit as st
import feedparser
import urllib.parse
import pandas as pd
import plotly.express as px
from simulation_logic import FIRESimulator

# --- ページ設定 ---
st.set_page_config(
    page_title="資産形成の羅針盤 | 米国株ニュース & FIRE",
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
.news-card { background: #1e2128; padding: 1.8rem; border-radius: 12px; border: 1px solid #30363d; margin-bottom: 1.5rem; }
.news-title { font-size: 1.3rem; font-weight: 700; color: #ffffff; margin-bottom: 0.8rem; }
.ad-banner-frame { background: linear-gradient(135deg, #004bb1 0%, #002d6b 100%); border: 2px solid #1f6feb; padding: 1.5rem; border-radius: 16px; text-align: center; margin: 2.5rem 0; box-shadow: 0 10px 25px rgba(31, 111, 235, 0.3); }
.ad-sub-text { color: #ffffff; font-size: 0.9rem; opacity: 0.9; margin-bottom: 1rem; }
@media (max-width: 768px) { .stMarkdown h1 { font-size: 1.5rem !important; } .ad-banner-frame img { max-width: 100%; height: auto; } }
</style>
""", unsafe_allow_html=True)

# --- セッション状態 ---
if 'fire_age_val' not in st.session_state: st.session_state.fire_age_val = 50

# --- ニュース取得 ---
@st.cache_data(ttl=3600)
def fetch_news(keyword):
    encoded_keyword = urllib.parse.quote(keyword)
    rss_url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=ja&gl=JP&ceid=JP:ja"
    try:
        feed = feedparser.parse(rss_url)
        return feed.entries
    except: return []

# --- コンテンツ ---
st.title("🧭 資産形成の羅針盤 (Wealth Compass)")
st.markdown("### 米国株・経済ニュース × FIREシミュレーション")
tab1, tab2 = st.tabs(["🇺🇸 最新ニュース", "🚀 FIREシミュレーター"])

with tab1:
    st.header("マーケット最新トピックス")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("📈 米国株", use_container_width=True): st.session_state.kw = "米国株式市場"
    with col2:
        if st.button("🏦 金利・中央銀行", use_container_width=True): st.session_state.kw = "FRB 金利 政策金利"
    with col3:
        if st.button("📉 インフレ指標", use_container_width=True): st.session_state.kw = "米国 CPI 物価"
    with col4:
        if st.button("💻 ハイテク・AI", use_container_width=True): st.session_state.kw = "NVIDIA AI株 マグニフィセント・セブン"

    current_kw = st.session_state.get('kw', '米国株式市場')
    st.markdown(f'<div class="ad-banner-frame"><div class="ad-sub-text">資産形成の必需品は楽天市場でチェック</div><a href="https://rpx.a8.net/svt/ejp?a8mat=4B3GYD+C0U5KI+2HOM+69P01&rakuten=y&a8ejpredirect=http%3A%2F%2Fhb.afl.rakuten.co.jp%2Fhgc%2F0ea62065.34400275.0ea62066.204f04c0%2Fa26050208529_4B3GYD_C0U5KI_2HOM_69P01%3Fpc%3Dhttp%253A%252F%252Fwww.rakuten.co.jp%252F%26m%3Dhttp%253A%252F%252Fm.rakuten.co.jp%252F" rel="nofollow"><img src="https://hbb.afl.rakuten.co.jp/hsb/0eb4bbc7.e9e6f789.0eb4bbaa.95151395/" border="0" style="border-radius: 4px;"></a><img border="0" width="1" height="1" src="https://www12.a8.net/0.gif?a8mat=4B3GYD+C0U5KI+2HOM+69P01" alt=""></div>', unsafe_allow_html=True)

    with st.spinner("ニュース取得中..."): news = fetch_news(current_kw)
    if not news: st.info("記事なし")
    else:
        for i, entry in enumerate(news[:15]):
            if i > 0 and i % 5 == 0:
                st.markdown(f'<div class="ad-banner-frame" style="background: rgba(30, 33, 40, 0.8); border-color: #30363d; display: flex; align-items: center; justify-content: center; gap: 20px;"><div style="text-align: left;"><div style="font-weight:700; color:white; font-size:1rem;">楽天市場</div><div style="color:#8b949e; font-size:0.8rem;">お買い物なら楽天市場へ</div></div><a href="https://rpx.a8.net/svt/ejp?a8mat=4B3GYD+C0U5KI+2HOM+5ZU29&rakuten=y&a8ejpredirect=http%3A%2F%2Fhb.afl.rakuten.co.jp%2Fhgc%2F0ea62065.34400275.0ea62066.204f04c0%2Fa26050208529_4B3GYD_C0U5KI_2HOM_5ZU29%3Fpc%3Dhttp%253A%252F%252Fwww.rakuten.co.jp%252F%26m%3Dhttp%253A%252F%252Fm.rakuten.co.jp%252F" rel="nofollow"><img src="https://hbb.afl.rakuten.co.jp/hsb/0eb4bbb2.58d658fd.0eb4bbaa.95151395/" border="0" style="border-radius: 4px;"></a><img border="0" width="1" height="1" src="https://www16.a8.net/0.gif?a8mat=4B3GYD+C0U5KI+2HOM+5ZU29" alt=""></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="news-card"><div class="news-title">{entry.title}</div><div class="news-date">🗓 {entry.published}</div><a href="{entry.link}" target="_blank" class="news-link">記事の詳細を確認する</a></div>', unsafe_allow_html=True)

with tab2:
    st.header("FIRE Simulator")
    col_input, col_chart = st.columns([1, 2])
    with col_input:
        st.subheader("条件設定")
        age = st.number_input("現在の年齢", 18, 80, 30)
        st.markdown("**運用資産額 (万円)**")
        c_reg, c_nisa = st.columns(2)
        with c_reg: reg_assets = st.number_input("特定口座", 0.00, 100000.00, 400.00, step=0.01)
        with c_nisa: nisa_assets = st.number_input("NISA口座", 0.00, 100000.00, 100.00, step=0.01)
        monthly_inv = st.number_input("毎月の積立額 (万円)", 0.00, 100.00, 10.00, step=0.01)
        ret_pre = st.number_input("積立期 (年利%)", 0.0, 100.0, 5.0, step=0.1)
        ret_post = st.number_input("リタイア後 (年利%)", 0.0, 100.0, 3.0, step=0.1)
        
        st.markdown("**リタイア・老後設定**")
        fire_age = st.number_input("リタイア希望年齢", 18, 100, st.session_state.fire_age_val)
        retirement_allowance = st.number_input("想定退職金 (万円)", 0.00, 10000.00, 0.00, step=0.01)
        
        exp_type = st.radio("生活費の単位", ["月額", "年額"], horizontal=True)
        exp_val = st.number_input(f"生活費 ({exp_type})", 0.00, 2000.00, 25.00 if exp_type == "月額" else 300.00, step=0.01)
        living_exp_monthly = exp_val if exp_type == "月額" else exp_val / 12
        
        c_p1, c_p2 = st.columns(2)
        with c_p1: pension_age = st.number_input("年金受給開始年齢", 60, 75, 65)
        with c_p2: pension_val = st.number_input("受給年金額 (月額)", 0.00, 50.00, 15.00, step=0.01)
        
        inf_rate = st.number_input("想定インフレ率 (%)", 0.0, 100.0, 1.0, step=0.1)

        if st.button("✨ 最短FIRE年齢を計算する", use_container_width=True):
            sim_rev = FIRESimulator()
            best_age = sim_rev.find_possible_fire_age({
                'currentAge': age, 'currentAssets': reg_assets + nisa_assets, 'nisaAssets': nisa_assets,
                'monthlyInvestment': monthly_inv, 'expectedReturnPre': ret_pre, 'livingExpense': living_exp_monthly,
                'expectedReturnPost': ret_post, 'inflationRate': inf_rate, 
                'pensionAmount': pension_val, 'pensionAge': pension_age, 'retirementAllowance': retirement_allowance
            })
            if best_age: st.session_state.fire_age_val = best_age; st.rerun()

    with col_chart:
        simulator = FIRESimulator()
        res = simulator.calculate({
            'currentAge': age, 'currentAssets': reg_assets + nisa_assets, 'nisaAssets': nisa_assets,
            'monthlyInvestment': monthly_inv, 'expectedReturnPre': ret_pre, 'fireAge': fire_age,
            'livingExpense': living_exp_monthly, 'expectedReturnPost': ret_post, 'inflationRate': inf_rate,
            'pensionAmount': pension_val, 'pensionAge': pension_age, 'retirementAllowance': retirement_allowance
        })
        df = pd.DataFrame(res['history'])
        df_plot = df.rename(columns={'regularAssets': '特定口座', 'nisaAssets': 'NISA口座'})
        df_plot['合計'] = df_plot['特定口座'] + df_plot['NISA口座']
        
        # グラフ描画（詳細ホバー設定）
        fig = px.area(df_plot, x='age', y=['特定口座', 'NISA口座'],
                      title="100歳までの資産推移予測",
                      labels={'value': '資産額 (万円)', 'age': '年齢', 'variable': '口座種別'},
                      color_discrete_map={'特定口座': '#1f6feb', 'NISA口座': '#238636'},
                      hover_data={'age': True, '特定口座': ':,.0f', 'NISA口座': ':,.0f', '合計': ':,.0f'},
                      template="plotly_dark")
        
        fig.update_layout(
            margin=dict(l=0, r=0, t=50, b=0),
            hovermode="x unified",
            xaxis=dict(range=[age, 100]),
            yaxis=dict(autorange=True, rangemode="tozero")
        )
        
        st.plotly_chart(fig, use_container_width=True)
        st.subheader("診断レポート")
        c1, c2 = st.columns(2)
        with c1:
            if res['exhaustionAge']: st.error(f"資産枯渇の予測: {res['exhaustionAge']}歳")
            else: st.success("資産寿命: 100歳以上を維持")
        with c2: st.metric("100歳時点の推定資産額", f"{res['finalAssets']:,.2f} 万円")
        st.markdown(f'<div class="ad-banner-frame" style="border-color: #238636; background: linear-gradient(135deg, #1b4d2a 0%, #0d2b17 100%);"><div class="ad-sub-text">FIRE達成への近道を探す</div><a href="https://rpx.a8.net/svt/ejp?a8mat=4B3GYD+C0U5KI+2HOM+69P01&rakuten=y&a8ejpredirect=http%3A%2F%2Fhb.afl.rakuten.co.jp%2Fhgc%2F0ea62065.34400275.0ea62066.204f04c0%2Fa26050208529_4B3GYD_C0U5KI_2HOM_69P01%3Fpc%3Dhttp%253A%252F%252Fwww.rakuten.co.jp%252F%26m%3Dhttp%253A%252F%252Fm.rakuten.co.jp%252F" rel="nofollow"><img src="https://hbb.afl.rakuten.co.jp/hsb/0eb4bbc7.e9e6f789.0eb4bbaa.95151395/" border="0" style="border-radius: 4px;"></a><img border="0" width="1" height="1" src="https://www12.a8.net/0.gif?a8mat=4B3GYD+C0U5KI+2HOM+69P01" alt=""></div>', unsafe_allow_html=True)
