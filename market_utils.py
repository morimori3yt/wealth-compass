import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os

# 統計データ (金融広報中央委員会 令和5年調査結果)
# 単位: 万円
STATS_DATA = {
    "単身世帯": {
        "平均値": {20: 121, 30: 594, 40: 825, 50: 1391, 60: 1468, 70: 1529},
        "中央値": {20: 9, 30: 100, 40: 47, 50: 80, 60: 210, 70: 500}
    },
    "二人以上世帯": {
        "平均値": {20: 249, 30: 601, 40: 889, 50: 1299, 60: 2026, 70: 1757},
        "中央値": {20: 30, 30: 150, 40: 220, 50: 350, 60: 700, 70: 700}
    }
}

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

def calc_fear_greed_score():
    """
    Fear & Greed Indexの計算ロジックのみを抽出（Streamlit非依存）
    """
    w = 1.0 / 7.0  # CNN準拠: 均等加重
    scores = {}
    
    # ① 株価モメンタム
    try:
        nk = yf.Ticker("^N225").history(period="160d")
        ma125 = nk['Close'].rolling(125).mean().iloc[-1]
        curr = nk['Close'].iloc[-1]
        pct_above = ((curr - ma125) / ma125) * 100
        scores['MOMENTUM'] = {'score': max(0, min(100, 50 + pct_above * 4)), 'value': f"{pct_above:+.2f}%"}
    except: scores['MOMENTUM'] = {'score': 50, 'value': 'N/A'}
    
    # ② 株価の強さ
    try:
        topix = yf.Ticker("1306.T").history(period="30d")
        mothers = yf.Ticker("2516.T").history(period="30d")
        topix_ret = (topix['Close'].iloc[-1] / topix['Close'].iloc[-20] - 1) * 100
        mothers_ret = (mothers['Close'].iloc[-1] / mothers['Close'].iloc[-20] - 1) * 100
        breadth = topix_ret - mothers_ret
        scores['STRENGTH'] = {'score': max(0, min(100, 50 + breadth * 5)), 'value': f"{breadth:+.2f}%"}
    except: scores['STRENGTH'] = {'score': 50, 'value': 'N/A'}
    
    # ③ 市場の広がり
    try:
        nk_vol = yf.Ticker("1321.T").history(period="70d")
        avg_vol = nk_vol['Volume'].rolling(50).mean().iloc[-1]
        curr_vol = nk_vol['Volume'].iloc[-5:].mean()
        vol_ratio = (curr_vol / avg_vol - 1) * 100 if avg_vol > 0 else 0
        scores['BREADTH'] = {'score': max(0, min(100, 50 + vol_ratio * 0.5)), 'value': f"{vol_ratio:+.1f}%"}
    except: scores['BREADTH'] = {'score': 50, 'value': 'N/A'}
    
    # ④ プット/コール比率代替
    try:
        vix_pc = yf.Ticker("^VIX").history(period="30d")
        vix_ma5 = vix_pc['Close'].rolling(5).mean().iloc[-1]
        vix_ma20 = vix_pc['Close'].rolling(20).mean().iloc[-1]
        vix_trend = ((vix_ma5 - vix_ma20) / vix_ma20) * 100
        scores['PUTCALL'] = {'score': max(0, min(100, 50 - vix_trend * 3)), 'value': f"{vix_trend:+.2f}%"}
    except: scores['PUTCALL'] = {'score': 50, 'value': 'N/A'}
    
    # ⑤ 市場のボラティリティ
    try:
        vix_data = yf.Ticker("^VIX").history(period="70d")
        vix_curr = vix_data['Close'].iloc[-1]
        vix_ma50 = vix_data['Close'].rolling(50).mean().iloc[-1]
        vix_diff = ((vix_curr - vix_ma50) / vix_ma50) * 100
        scores['VOLATILITY'] = {'score': max(0, min(100, 50 - vix_diff * 2)), 'value': f"VIX {vix_curr:.1f}"}
    except: scores['VOLATILITY'] = {'score': 50, 'value': 'N/A'}
    
    # ⑥ 安全資産への逃避
    try:
        stk = yf.Ticker("^N225").history(period="30d")
        bnd = yf.Ticker("TLT").history(period="30d")
        stk_ret = (stk['Close'].iloc[-1] / stk['Close'].iloc[-20] - 1) * 100
        bnd_ret = (bnd['Close'].iloc[-1] / bnd['Close'].iloc[-20] - 1) * 100
        safe_haven = stk_ret - bnd_ret
        scores['SAFEHAVEN'] = {'score': max(0, min(100, 50 + safe_haven * 4)), 'value': f"{safe_haven:+.2f}%"}
    except: scores['SAFEHAVEN'] = {'score': 50, 'value': 'N/A'}
    
    # ⑦ ジャンク債需要 (LQD vs IEF)
    try:
        lqd = yf.Ticker("LQD").history(period="30d")
        ief = yf.Ticker("IEF").history(period="30d")
        lqd_ret = (lqd['Close'].iloc[-1] / lqd['Close'].iloc[-20] - 1) * 100
        ief_ret = (ief['Close'].iloc[-1] / ief['Close'].iloc[-20] - 1) * 100
        junk_demand = lqd_ret - ief_ret
        scores['JUNKBOND'] = {'score': max(0, min(100, 50 + junk_demand * 10)), 'value': f"{junk_demand:+.2f}%"}
    except: scores['JUNKBOND'] = {'score': 50, 'value': 'N/A'}
    
    final_score = sum(s['score'] for s in scores.values()) * w
    return final_score, scores

def generate_fg_gauge_image(output_path="fg_gauge.jpg"):
    """
    Fear & Greed Indexのゲージを画像として保存する。
    kaleidoが必要。
    """
    score, details = calc_fear_greed_score()
    
    # ラベル決定
    if score <= 20: label, color = "極度の恐怖", "#EF4444"
    elif score <= 40: label, color = "恐怖", "#F59E0B"
    elif score <= 60: label, color = "中立", "#94A3B8"
    elif score <= 80: label, color = "強欲", "#10B981"
    else: label, color = "極度の強欲", "#059669"
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': f"市場心理: {label}", 'font': {'size': 24, 'color': color, 'family': "Meiryo, sans-serif"}},
        gauge = {
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "#1E293B"},
            'bar': {'color': color},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#94A3B8",
            'steps': [
                {'range': [0, 20], 'color': 'rgba(239, 68, 68, 0.1)'},
                {'range': [20, 40], 'color': 'rgba(245, 158, 11, 0.1)'},
                {'range': [40, 60], 'color': 'rgba(148, 163, 184, 0.1)'},
                {'range': [60, 80], 'color': 'rgba(16, 185, 129, 0.1)'},
                {'range': [80, 100], 'color': 'rgba(5, 150, 105, 0.1)'}
            ],
            'threshold': {
                'line': {'color': "#0F172A", 'width': 4},
                'thickness': 0.75,
                'value': score
            }
        }
    ))
    
    fig.update_layout(
        paper_bgcolor = "white",
        font = {'color': "#1E293B", 'family': "Meiryo, sans-serif"},
        width=800,
        height=500,
        margin=dict(l=40, r=40, t=80, b=40)
    )
    
    try:
        fig.write_image(output_path, scale=2)
        return output_path
    except Exception as e:
        print(f"画像生成失敗: {e}")
        return None
