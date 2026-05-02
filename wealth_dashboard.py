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

/* ニュースカード */
.news-card {
    background: #1e2128;
    padding: 1.8rem;
    border-radius: 12px;
    border: 1px solid #30363d;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.news-title {
    font-size: 1.3rem;
    font-weight: 700;
    color: #ffffff;
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
    border: 1px solid #58a6ff;
    padding: 6px 16px;
    border-radius: 6px;
}

/* プレミアム広告バナー枠 */
.ad-banner-frame {
    background: linear-gradient(135deg, #004bb1 0%, #002d6b 100%);
    border: 2px solid #1f6feb;
    padding: 1.5rem;
    border-radius: 16px;
    text-align: center;
    margin: 2.5rem 0;
    box-shadow: 0 10px 25px rgba(31, 111, 235, 0.3);
}

.ad-sub-text {
    color: #ffffff;
    font-size: 0.9rem;
    opacity: 0.9;
    margin-bottom: 1rem;
    font-weight: 600;
}

@media (max-width: 768px) {
    .stMarkdown h1 {
        font-size: 1.5rem !important;
    }
    .ad-banner-frame {
        padding: 1rem;
    }
    /* スマホで横長の画像がはみ出ないように */
    .ad-banner-frame img {
        max-width: 100%;
        height: auto;
    }
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

tab1, tab2 = st.tabs(["🇺🇸 最新ニュース", "🚀 FIREシミュレーター"])

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
    
    # プレミアムバナー 1 (468x60) - 新しいバナー
    st.markdown(f"""
    <div class="ad-banner-frame">
        <div class="ad-sub-text">資産形成の必需品は楽天市場でチェック</div>
        <a href="https://rpx.a8.net/svt/ejp?a8mat=4B3GYD+C0U5KI+2HOM+69P01&rakuten=y&a8ejpredirect=http%3A%2F%2Fhb.afl.rakuten.co.jp%2Fhgc%2F0ea62065.34400275.0ea62066.204f04c0%2Fa26050208529_4B3GYD_C0U5KI_2HOM_69P01%3Fpc%3Dhttp%253A%252F%252Fwww.rakuten.co.jp%252F%26m%3Dhttp%253A%252F%252Fm.rakuten.co.jp%252F" rel="nofollow">
        <img src="https://hbb.afl.rakuten.co.jp/hsb/0eb4bbc7.e9e6f789.0eb4bbaa.95151395/" border="0" style="border-radius: 4px;"></a>
        <img border="0" width="1" height="1" src="https://www12.a8.net/0.gif?a8mat=4B3GYD+C0U5KI+2HOM+69P01" alt="">
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("最新ニュースを取得中..."):
        news = fetch_news(current_kw)
    
    if not news:
        st.info("関連記事が見つかりませんでした。")
    else:
        for i, entry in enumerate(news[:15]):
            if i > 0 and i % 5 == 0:
                # プレミアムバナー 2 (120x60) - 継続使用
                st.markdown(f"""
                <div class="ad-banner-frame" style="background: rgba(30, 33, 40, 0.8); border-color: #30363d; display: flex; align-items: center; justify-content: center; gap: 20px;">
                    <div style="text-align: left;">
                        <div style="font-weight:700; color:white; font-size:1rem;">楽天市場</div>
                        <div style="color:#8b949e; font-size:0.8rem;">お買い物なら楽天市場へ</div>
                    </div>
                    <a href="https://rpx.a8.net/svt/ejp?a8mat=4B3GYD+C0U5KI+2HOM+5ZU29&rakuten=y&a8ejpredirect=http%3A%2F%2Fhb.afl.rakuten.co.jp%2Fhgc%2F0ea62065.34400275.0ea62066.204f04c0%2Fa26050208529_4B3GYD_C0U5KI_2HOM_5ZU29%3Fpc%3Dhttp%253A%252F%252Fwww.rakuten.co.jp%252F%26m%3Dhttp%253A%252F%252Fm.rakuten.co.jp%252F" rel="nofollow">
                    <img src="https://hbb.afl.rakuten.co.jp/hsb/0eb4bbb2.58d658fd.0eb4bbaa.95151395/" border="0" style="border-radius: 4px;"></a>
                    <img border="0" width="1" height="1" src="https://www16.a8.net/0.gif?a8mat=4B3GYD+C0U5KI+2HOM+5ZU29" alt="">
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
            reg_assets = st.number_input("特定口座", 0.00, 100000.00, 400.00, step=0.01)
        with c_nisa:
            nisa_assets = st.number_input("NISA口座", 0.00, 100000.00, 100.00, step=0.01)
        
        total_assets = reg_assets + nisa_assets
        st.info(f"合計資産額: {total_assets:,.2f} 万円")
        
        monthly_inv = st.number_input("毎月の積立額 (万円)", 0.00, 100.00, 10.00, step=0.01)
        
        st.markdown("**期待利回り (%)**")
        ret_pre = st.number_input("積立期 (年利)", 0.0, 100.0, 5.0, step=0.1)
        ret_post = st.number_input("リタイア後 (年利)", 0.0, 100.0, 3.0, step=0.1)
        
        st.markdown("**リタイア後の支出・収入**")
        fire_age = st.number_input("リタイア希望年齢", 18, 100, 50, key="fire_age_input")
        
        exp_type = st.radio("生活費の単位", ["月額", "年額"], horizontal=True)
        exp_val = st.number_input(f"リタイア後の生活費 ({exp_type})", 0.00, 2000.00, 25.00 if exp_type == "月額" else 300.00, step=0.01)
        living_exp_monthly = exp_val if exp_type == "月額" else exp_val / 12
        
        pension_val = st.number_input("受給年金額 (月額/万円)", 0.00, 50.00, 15.00, step=0.01)
        inf_rate = st.number_input("想定インフレ率 (%)", 0.0, 100.0, 1.0, step=0.1)

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
            st.metric("100歳時点の推定資産額", f"{res['finalAssets']:,.2f} 万円")

        # FIRE加速バナー (468x60) - 新しいバナー
        st.markdown(f"""
        <div class="ad-banner-frame" style="border-color: #238636; background: linear-gradient(135deg, #1b4d2a 0%, #0d2b17 100%);">
            <div class="ad-sub-text">FIRE達成への近道を探す</div>
            <a href="https://rpx.a8.net/svt/ejp?a8mat=4B3GYD+C0U5KI+2HOM+69P01&rakuten=y&a8ejpredirect=http%3A%2F%2Fhb.afl.rakuten.co.jp%2Fhgc%2F0ea62065.34400275.0ea62066.204f04c0%2Fa26050208529_4B3GYD_C0U5KI_2HOM_69P01%3Fpc%3Dhttp%253A%252F%252Fwww.rakuten.co.jp%252F%26m%3Dhttp%253A%252F%252Fm.rakuten.co.jp%252F" rel="nofollow">
            <img src="https://hbb.afl.rakuten.co.jp/hsb/0eb4bbc7.e9e6f789.0eb4bbaa.95151395/" border="0" style="border-radius: 4px;"></a>
            <img border="0" width="1" height="1" src="https://www12.a8.net/0.gif?a8mat=4B3GYD+C0U5KI+2HOM+69P01" alt="">
        </div>
        """, unsafe_allow_html=True)
