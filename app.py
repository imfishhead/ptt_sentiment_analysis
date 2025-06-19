# app.py

import streamlit as st
import pandas as pd
import datetime
import plotly.graph_objects as go
from data_fetcher import get_ptt_articles_from_db
from sentiment_analyzer import get_sentiment_model, analyze_sentiment_batch # 導入你更新後的函數
from config import EMOTIONS_NAMES

# --- Streamlit 應用程式配置 ---
st.set_page_config(
    page_title="PTT 看板情感分析儀",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 PTT 看板情感趨勢分析儀")
st.markdown("探索 PTT 看板文章的情感波動，掌握社群脈動。")

# --- 輔助函數 (保持不變) ---

@st.cache_data(show_spinner="⏳ 正在聚合情感數據...")
def aggregate_emotions_by_hour(df: pd.DataFrame) -> pd.DataFrame:
    """每小時聚合情感分數."""
    if df.empty:
        return pd.DataFrame()

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')

    for emo in EMOTIONS_NAMES:
        if emo not in df.columns:
            df[emo] = 0.0
        df[emo] = pd.to_numeric(df[emo], errors='coerce').fillna(0)

    agg_dict = {emo: 'mean' for emo in EMOTIONS_NAMES}
    hourly_emotions = df.resample('H').agg(agg_dict).fillna(0)
    return hourly_emotions

def plot_radar_chart(data_row: pd.Series, emotions: list) -> go.Figure:
    """繪製八角向量圖 (雷達圖)。"""
    if data_row.empty or not any(data_row.get(emo, 0) > 0 for emo in emotions):
        fig = go.Figure()
        fig.add_annotation(
            text="無情感數據可顯示，請選擇有內容的時間點。",
            x=0.5, y=0.5, showarrow=False, font_size=16, opacity=0.7
        )
        fig.update_layout(title="情感八角向量圖", title_x=0.5)
        return fig

    categories = [f"{EMOTION_NAMES_ZH.get(emo, emo)} {EMOTION_EMOJIS.get(emo, '')}" for emo in emotions]
    values = [data_row.get(emotion, 0) for emotion in emotions]
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name='情感程度',
        marker=dict(color='deepskyblue', line=dict(color='dodgerblue', width=2)),
        opacity=0.8
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                tickvals=[0, 0.25, 0.5, 0.75, 1],
                gridcolor='lightgray',
                linecolor='gray'
            ),
            bgcolor='white',
            gridshape='linear'
        ),
        showlegend=False,
        title="情感八角向量圖",
        title_x=0.5,
        font=dict(family="Arial, sans-serif", size=12)
    )
    return fig

# 從 sentiment_analyzer 導入這些額外的映射，用於顯示
from sentiment_analyzer import emotion_names_zh as EMOTION_NAMES_ZH
from sentiment_analyzer import emotion_emojis as EMOTION_EMOJIS


# --- 側邊欄控制項 ---
with st.sidebar:
    st.header("設定選項")
    board_options = ['Gossiping', 'WomenTalk', 'Tech_Job', 'Boy-Girl', 'Stock', 'NBA']
    selected_board = st.selectbox("選擇 PTT 看板", board_options, help="選擇你感興趣的 PTT 看板進行分析。")

    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=6)
    end_date = today
    st.write(f"分析區間：{start_date} ~ {end_date}")

    if st.button("🔄 抓取並分析最新文章", help=f"點擊以獲取 {selected_board} 看板過去七天的文章，並重新進行情感分析。", use_container_width=True):
        st.session_state['trigger_fetch'] = True
        st.session_state['board_for_fetch'] = selected_board
        st.session_state['start_date'] = start_date
        st.session_state['end_date'] = end_date
        st.success("已排程數據抓取與分析！請稍候...")

# --- 主內容區域 ---

if st.session_state.get('trigger_fetch', False):
    # 先清空右側資料並顯示 loading 訊息
    st.session_state['hourly_data'] = pd.DataFrame()
    st.session_state['articles_df'] = pd.DataFrame()
    st.info("抓取文章中，請稍後…")
    
    # 載入情感分析模型 (現在它只是返回一個標誌)
    sentiment_model_placeholder = get_sentiment_model()

    articles_df = get_ptt_articles_from_db(
        board=st.session_state['board_for_fetch']
    )

    if not articles_df.empty:
        articles_df = analyze_sentiment_batch(articles_df, sentiment_model_placeholder)
        hourly_data = aggregate_emotions_by_hour(articles_df)
        st.session_state['hourly_data'] = hourly_data
        st.session_state['articles_df'] = articles_df
        st.success("✅ 文章抓取與情感分析完成！")
        # 直接顯示分析圖
        min_time = hourly_data.index.min().to_pydatetime()
        max_time = hourly_data.index.max().to_pydatetime()
        st.subheader("🕰️ 情感趨勢時間軸")
        if min_time == max_time:
            selected_time = min_time
            st.info(f"僅有一個時段：{min_time.strftime('%Y/%m/%d %H:00')}")
        else:
            selected_time = st.slider(
                "選擇時間點以查看該小時的情感分佈",
                min_value=min_time,
                max_value=max_time,
                value=max_time,
                step=datetime.timedelta(hours=1),
                format="YYYY/MM/DD HH:00",
                help="拖動滑桿以查看不同時間點的文章情感分佈。"
            )
        time_diffs_td = hourly_data.index - selected_time
        time_diff_seconds = time_diffs_td.to_series().apply(lambda x: x.total_seconds()).abs()
        closest_time_index_loc = time_diff_seconds.argmin()
        closest_time_data = hourly_data.iloc[closest_time_index_loc]
        st.subheader("🌐 即時情感八角向量圖")
        st.plotly_chart(plot_radar_chart(closest_time_data, EMOTIONS_NAMES), use_container_width=True)
        st.subheader("📈 過去七天每小時情感分數 (表格)")
        st.dataframe(hourly_data.reset_index().rename(columns={'index': '時間'}), use_container_width=True, height=300)
        csv_data = hourly_data.to_csv(index=True).encode('utf-8')
        st.download_button(
            label="下載情感數據 (CSV)",
            data=csv_data,
            file_name=f"{selected_board}_sentiment_data.csv",
            mime="text/csv",
            help="下載當前看板的情感數據。"
        )
        if st.button("顯示已抓取的原始文章資料"):
            st.dataframe(st.session_state['articles_df'], use_container_width=True, height=400)
    else:
        st.warning("⚠️ 沒有找到符合條件的文章，請嘗試其他看板或時間範圍。")
        st.session_state['hourly_data'] = pd.DataFrame()
        st.session_state['articles_df'] = pd.DataFrame()
    st.session_state['trigger_fetch'] = False
elif (
    ('hourly_data' not in st.session_state or st.session_state['hourly_data'].empty)
    and ('articles_df' not in st.session_state or st.session_state['articles_df'].empty)
    and not st.session_state.get('trigger_fetch', False)
):
    st.info("👋 歡迎使用！請從左側選擇看板，然後點擊「抓取並分析最新文章」按鈕開始。")

# --- 顯示結果 (當數據存在時) ---

if 'hourly_data' in st.session_state and not st.session_state['hourly_data'].empty:
    hourly_data = st.session_state['hourly_data']

    # 確保時間戳是 Python datetime 對象
    min_time = hourly_data.index.min().to_pydatetime()
    max_time = hourly_data.index.max().to_pydatetime()

    st.subheader("🕰️ 情感趨勢時間軸")
    if min_time == max_time:
        selected_time = min_time
        st.info(f"僅有一個時段：{min_time.strftime('%Y/%m/%d %H:00')}")
    else:
        selected_time = st.slider(
            "選擇時間點以查看該小時的情感分佈",
            min_value=min_time,
            max_value=max_time,
            value=max_time,
            step=datetime.timedelta(hours=1),
            format="YYYY/MM/DD HH:00",
            help="拖動滑桿以查看不同時間點的文章情感分佈。"
        )

    # 找到最接近 slider 選定時間的數據點
    time_diffs_td = hourly_data.index - selected_time
    time_diff_seconds = time_diffs_td.to_series().apply(lambda x: x.total_seconds()).abs()
    closest_time_index_loc = time_diff_seconds.argmin()
    closest_time_data = hourly_data.iloc[closest_time_index_loc]

    st.subheader("🌐 即時情感八角向量圖")
    st.plotly_chart(plot_radar_chart(closest_time_data, EMOTIONS_NAMES), use_container_width=True)

    st.subheader("📈 過去七天每小時情感分數 (表格)")
    st.dataframe(hourly_data.reset_index().rename(columns={'index': '時間'}), use_container_width=True, height=300)
    
    csv_data = hourly_data.to_csv(index=True).encode('utf-8')
    st.download_button(
        label="下載情感數據 (CSV)",
        data=csv_data,
        file_name=f"{selected_board}_sentiment_data.csv",
        mime="text/csv",
        help="下載當前看板的情感數據。"
    )

    # 新增：顯示原始文章資料按鈕
    if st.button("顯示已抓取的原始文章資料"):
        st.dataframe(st.session_state['articles_df'], use_container_width=True, height=400)

st.markdown("---")
st.caption("數據來源：PTT。情感分析結果來自詞典與規則。")