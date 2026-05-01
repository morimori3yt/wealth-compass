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

html, body, [class*="css"] {
    font-family: 'Inter', 'Noto Sans JP', sans-serif;
}

.main {
    background-color: #0e1117;
}

/* ニュースカードの視認性向上 */
.news-card {
    background: #1e2128; /* より濃い背景色に変更 */
    padding: 1.8rem;
    border-radius: 12px;
    border: 1px solid #30363d;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    transition: transform 0.2s ease;
}

.news-card:hover {
    transform: translateY(-2px);
    border-color: #58a6ff;
}

.news-title {
    font-size: 1.35rem; /* サイズアップ */
    font-weight: 700;
    color: #ffffff; /* 完全な白に */
    margin-bottom: 0.8rem;
    line-height: 1.4;
}

.news-date {
    font-size: 0.9rem;
    color: #8b949e;
    margin-bottom: 1rem;
}

.news-link {
    display: inline-block;
    color: #58a6ff !important;
    text-decoration: none;
    font-weight: 700;
    font-size: 1rem;
    border: 1px solid #58a6ff;
    padding: 6px 16px;
    border-radius: 6px;
    transition: background 0.2s;
}

.news-link:hover {
    background: rgba(88, 166, 255, 0.1);
}

/* 広告コンテナ */
.ad-container {
    background: linear-gradient(135deg, rgba(31, 111, 235, 0.15) 0%, rgba(13, 71, 161, 0.15) 100%);
    border: 1px solid #1f6feb;
    padding: 1.8rem;
    border-radius: 12px;
    text-align: center;
    margin: 2rem 0;
}

.ad-badge {
    background: #1f6feb;
    color: white;
    padding: 3px 12px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 800;
    margin-bottom: 1rem;
    display: inline-block;
}

.stButton>button {
    border-radius: 6px;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# --- データ取得処理 ---
@st.cache_data(ttl=3600)
def fetch_news(keyword):
    encoded_keyword = urllib.parse.quote(keyword)
    rss_url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=ja&gl=JP&ceid=JP:ja"
    try:
        feed = feedparser.parse(rss_url)
        return feed.entries
    except:
        return []

# --- メインコンテンツ ---
st.title("🧭 資産形成の羅針盤 (Wealth Compass)")
st.markdown("### 米国株・経済ニュース × FIREシミュレーション")

tab1, tab2 = st.tabs(["🇺🇸 米国株・経済最新ニュース", "🚀 FIREシミュレーター"])

with tab1:
    st.header("マーケット最新トピックス")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("📈 米国株", use_container_width=True):
            st.session_state.kw = "米国株式市場"
    with col2:
        if st.button("🏦 金利・中央銀行", use_container_width=True):
            st.session_state.kw = "FRB 金利 政策金利"
    with col3:
        if st.button("📉 インフレ指標", use_container_width=True):
            st.session_state.kw = "米国 CPI 物価"
    with col4:
        if st.button("💻 ハイテク・AI", use_container_width=True):
            st.session_state.kw = "NVIDIA AI株 マグニフィセント・セブン"

    current_kw = st.session_state.get('kw', '米国株式市場')
    
    # 広告枠 1
    st.markdown(f"""
    <div class="ad-container">
        <span class="ad-badge">スポンサー情報</span>
        <div style="font-weight:700; color:white; font-size:1.2rem; margin-bottom:0.5rem;">米国株投資に最適な証券口座を比較</div>
        <p style="color: #c9d1d9; font-size: 0.95rem;">低コストで米国株・ETFに投資。今なら口座開設キャンペーン実施中。</p>
        <a href="#" style="color:#58a6ff; font-weight:700; text-decoration:none;">詳細・無料口座開設はこちら 👉</a>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("最新ニュースを取得中..."):
        news = fetch_news(current_kw)
    
    if not news:
        st.info("関連記事が見つかりませんでした。")
    else:
        for i, entry in enumerate(news[:15]):
            if i > 0 and i % 5 == 0:
                st.markdown(f"""
                <div class="ad-container" style="background: rgba(48, 54, 61, 0.5); border-color: #30363d;">
                    <span class="ad-badge" style="background: #30363d;">おすすめ</span>
                    <div style="font-weight:700; color:white; font-size:1.1rem; margin-bottom:0.5rem;">一生モノの資産運用スキルを身につける</div>
                    <p style="color: #c9d1d9; font-size: 0.9rem;">プロが教える投資スクールの無料体験セミナー実施中。</p>
                    <a href="#" style="color:#58a6ff; font-weight:700; text-decoration:none;">無料セミナーを予約する 👉</a>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="news-card">
                <div class="news-title">{entry.title}</div>
                <div class="news-date">🗓 {entry.published}</div>
                <a href="{entry.link}" target="_blank" class="news-link">記事の詳細を確認する</a>
            </div>
            """, unsafe_allow_html=True)

with tab2:
    st.header("FIRE Simulator")
    st.markdown("資産形成のシミュレーションと、目標達成までの最短ルートを可視化します。")
    
    col_input, col_chart = st.columns([1, 2])
    
    with col_input:
        st.subheader("条件設定")
        age = st.number_input("現在の年齢", 18, 80, 30, key="age_input")
        
        st.markdown("**現在の運用資産額 (万円)**")
        c_reg, c_nisa = st.columns(2)
        with c_reg:
            reg_assets = st.number_input("特定口座", 0, 100000, 400)
        with c_nisa:
            nisa_assets = st.number_input("NISA口座", 0, 100000, 100)
        
        total_assets = reg_assets + nisa_assets
        st.info(f"合計資産額: {total_assets:,} 万円")
        
        monthly_inv = st.number_input("毎月の積立額 (万円)", 0, 100, 10)
        
        st.markdown("**期待利回り (%)**")
        ret_pre = st.slider("積立期 (年利)", 0.0, 15.0, 5.0)
        ret_post = st.slider("リタイア後 (年利)", 0.0, 15.0, 3.0)
        
        st.markdown("**リタイア後の支出・収入**")
        fire_age = st.number_input("リタイア希望年齢", 18, 100, 50, key="fire_age_input")
        
        exp_type = st.radio("生活費の単位", ["月額", "年額"], horizontal=True)
        exp_val = st.number_input(f"リタイア後の生活費 ({exp_type})", 0, 2000, 25 if exp_type == "月額" else 300)
        living_exp_monthly = exp_val if exp_type == "月額" else exp_val / 12
        
        pension_val = st.number_input("受給年金額 (月額/万円)", 0, 50, 15)
        inf_rate = st.slider("想定インフレ率 (%)", 0.0, 10.0, 1.0)

        if st.button("✨ 最短FIRE年齢を計算する", use_container_width=True):
            sim_rev = FIRESimulator()
            best_age = sim_rev.find_possible_fire_age({
                'currentAge': age,
                'currentAssets': total_assets,
                'nisaAssets': nisa_assets,
                'monthlyInvestment': monthly_inv,
                'expectedReturnPre': ret_pre,
                'livingExpense': living_exp_monthly,
                'expectedReturnPost': ret_post,
                'inflationRate': inf_rate,
                'pensionAmount': pension_val
            })
            if best_age:
                st.success(f"最短 {best_age} 歳でFIRE可能です！")
                st.session_state.fire_age_input = best_age
                st.rerun()
            else:
                st.warning("現在の条件では100歳までにFIREを達成することは困難です。")

    with col_chart:
        simulator = FIRESimulator()
        res = simulator.calculate({
            'currentAge': age,
            'currentAssets': total_assets,
            'nisaAssets': nisa_assets,
            'monthlyInvestment': monthly_inv,
            'expectedReturnPre': ret_pre,
            'fireAge': st.session_state.get('fire_age_input', fire_age),
            'livingExpense': living_exp_monthly,
            'expectedReturnPost': ret_post,
            'inflationRate': inf_rate,
            'pensionAmount': pension_val
        })
        
        df = pd.DataFrame(res['history'])
        fig = px.area(df, x='age', y=['regularAssets', 'nisaAssets'], 
                      title="将来の資産推移予測",
                      labels={'value': '資産額 (万円)', 'age': '年齢', 'variable': '口座種別'},
                      color_discrete_map={'regularAssets': '#1f6feb', 'nisaAssets': '#238636'},
                      template="plotly_dark")
        
        fig.update_layout(margin=dict(l=0, r=0, t=50, b=0), hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("診断レポート")
        c1, c2 = st.columns(2)
        with c1:
            if res['exhaustionAge']:
                st.error(f"資産枯渇の予測: {res['exhaustionAge']}歳")
            else:
                st.success("資産寿命: 100歳以上を維持")
        with c2:
            st.metric("100歳時点の推定資産額", f"{int(res['finalAssets']):,} 万円")

        st.markdown(f"""
        <div class="ad-container" style="border-color: #238636; background: rgba(35, 134, 54, 0.1);">
            <span class="ad-badge" style="background: #238636;">FIRE加速プラン</span>
            <div style="font-weight:700; color:white; font-size:1.1rem; margin-bottom:0.5rem;">【無料】お金のプロによる家計診断</div>
            <p style="color: #c9d1d9; font-size: 0.9rem;">あなたのライフプランに基づいた最適な投資戦略をアドバイス。</p>
            <a href="#" style="color:#3fb950; font-weight:700; text-decoration:none;">無料相談の予約はこちら 👉</a>
        </div>
        """, unsafe_allow_html=True)
