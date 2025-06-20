# app.py

import streamlit as st
import pandas as pd
import datetime
import plotly.graph_objects as go
from data_fetcher import get_ptt_articles_from_db
from sentiment_analyzer import get_sentiment_model, analyze_sentiment_batch # 導入你更新後的函數
from config import EMOTIONS_NAMES
import sqlite3

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
    
    # 動態計算軸線範圍
    max_value = max(values) if values else 0.1
    if max_value <= 0.1:
        # 如果最大值很小，設定一個合適的範圍
        axis_max = 0.1
        tick_vals = [0, 0.02, 0.04, 0.06, 0.08, 0.1]
    elif max_value <= 0.5:
        # 中等範圍
        axis_max = 0.5
        tick_vals = [0, 0.1, 0.2, 0.3, 0.4, 0.5]
    else:
        # 大範圍
        axis_max = 1.0
        tick_vals = [0, 0.25, 0.5, 0.75, 1.0]
    
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
                range=[0, axis_max],
                tickvals=tick_vals,
                ticktext=[f"{val:.3f}" for val in tick_vals],  # 顯示三位小數
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

def display_analysis_results(selected_board, hourly_data, articles_df, mode='exist'):
    """顯示分析結果的統一函數"""
    min_time = hourly_data.index.min().to_pydatetime()
    max_time = hourly_data.index.max().to_pydatetime()
    
    st.subheader(f"[{selected_board}] 七天情感趨勢分析")
    st.subheader("🕰️ 情感趨勢時間軸")
    slider_needed = min_time != max_time
    if slider_needed:
        selected_time = st.slider(
            "選擇時間點以查看該小時的情感分佈",
            min_value=min_time,
            max_value=max_time,
            value=max_time,
            step=datetime.timedelta(hours=1),
            format="YYYY/MM/DD HH:00",
            help="拖動滑桿以查看不同時間點的文章情感分佈。",
            key=f"sentiment_time_slider_{mode}"
        )
    else:
        selected_time = min_time
        st.info(f"僅有一個時段：{min_time.strftime('%Y/%m/%d %H:00')}")

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
        st.dataframe(articles_df, use_container_width=True, height=400)
        st.info(f"目前已抓取並累積 {len(articles_df)} 篇文章（含本次新抓取）")

# 從 sentiment_analyzer 導入這些額外的映射，用於顯示
from sentiment_analyzer import emotion_names_zh as EMOTION_NAMES_ZH
from sentiment_analyzer import emotion_emojis as EMOTION_EMOJIS

# --- SQLite 快取輔助函數 ---
def save_board_to_sqlite(board, df, db_path='ptt_cache.db'):
    conn = sqlite3.connect(db_path)
    df.to_sql(f'ptt_{board}', conn, if_exists='replace', index=False)
    conn.close()

def load_board_from_sqlite(board, db_path='ptt_cache.db'):
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        # 檢查表格是否存在
        cursor = conn.cursor()
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='ptt_{board}'")
        if cursor.fetchone() is None:
            # 表格不存在，回傳空 DataFrame
            return pd.DataFrame()
        
        # 只載入近七天
        seven_days_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
        query = f"SELECT * FROM ptt_{board} WHERE timestamp >= '{seven_days_ago}'"
        df = pd.read_sql(query, conn, parse_dates=['timestamp'])
        return df
    except Exception as e:
        # 任何錯誤都回傳空 DataFrame
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

# --- CSV 備用數據讀取函數 ---
def load_csv_backup(board):
    """從專案目錄讀取 CSV 備用數據"""
    import os
    import glob
    
    # 尋找符合看板名稱的 CSV 檔案
    csv_patterns = [
        f"{board.lower()}_*.csv",
        f"{board}_*.csv", 
        f"*{board.lower()}*.csv",
        f"*{board}*.csv"
    ]
    
    for pattern in csv_patterns:
        csv_files = glob.glob(pattern)
        if csv_files:
            # 找到檔案，讀取第一個
            csv_file = csv_files[0]
            try:
                st.info(f"📁 讀取備用 CSV 檔案：{csv_file}")
                df = pd.read_csv(csv_file, parse_dates=['timestamp'])
                
                # 檢查必要的欄位
                required_columns = ['timestamp', 'content', 'title', 'author', 'board']
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    st.warning(f"CSV 檔案缺少必要欄位：{missing_columns}")
                    continue
                
                # 取消時間篩選，直接讀取所有數據
                if not df.empty:
                    st.success(f"✅ 成功讀取 {len(df)} 篇文章（來自 CSV 備用數據）")
                    return df
                else:
                    st.warning("CSV 檔案是空的")
                    
            except Exception as e:
                st.error(f"讀取 CSV 檔案時發生錯誤：{str(e)}")
                continue
    
    st.warning("❌ 沒有找到可用的 CSV 備用數據檔案")
    return pd.DataFrame()

# --- 側邊欄控制項 ---
with st.sidebar:
    st.header("設定選項")
    board_options = ['Gossiping', 'WomenTalk', 'Tech_Job', 'Boy-Girl', 'Stock', 'NBA']
    selected_board = st.selectbox("選擇 PTT 看板", board_options, help="選擇你感興趣的 PTT 看板進行分析。")

    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=6)
    end_date = today
    st.write(f"分析區間：{start_date} ~ {end_date}")

    # 啟動時自動從 SQLite 載入 cache
    if 'articles_df_dict' not in st.session_state:
        st.session_state['articles_df_dict'] = {}
    if 'hourly_data_dict' not in st.session_state:
        st.session_state['hourly_data_dict'] = {}
    
    # 移除自動載入，只在按下按鈕時才載入資料

    # 依據目前 dropdown 選擇顯示 cache 數量
    cache_count = 0
    latest_time_str = "無"
    if selected_board in st.session_state['articles_df_dict'] and isinstance(st.session_state['articles_df_dict'][selected_board], pd.DataFrame):
        cache_count = len(st.session_state['articles_df_dict'][selected_board])
        if cache_count > 0:
            latest_time = st.session_state['articles_df_dict'][selected_board]['timestamp'].max()
            latest_time_str = latest_time.strftime('%Y/%m/%d %H:%M')
    st.write(f"目前 Cache 已有 {cache_count} 篇文章，最新抓取時間：{latest_time_str}")

    if st.button("🔄 抓取並分析最新文章", help=f"點擊以獲取 {selected_board} 看板過去七天的文章，並重新進行情感分析。", use_container_width=True):
        st.session_state['trigger_fetch'] = True
        st.session_state['board_for_fetch'] = selected_board
        st.session_state['start_date'] = start_date
        st.session_state['end_date'] = end_date
        st.success("已排程數據抓取與分析！請稍候...")

# --- 主內容區域 ---

if st.session_state.get('trigger_fetch', False):
    # 不要清空 cache，保留用於增量抓取
    st.session_state['hourly_data_dict'][selected_board] = pd.DataFrame()

    # 載入現有資料（如果存在）
    if selected_board not in st.session_state['articles_df_dict']:
        st.session_state['articles_df_dict'][selected_board] = load_board_from_sqlite(selected_board)

    sentiment_model_placeholder = get_sentiment_model()

    # 取得目前 cache 最新文章時間
    last_time = None
    if selected_board in st.session_state['articles_df_dict'] and not st.session_state['articles_df_dict'][selected_board].empty:
        last_time = st.session_state['articles_df_dict'][selected_board]['timestamp'].max()
        st.info(f"現有 cache 最新文章時間：{last_time}")
    
    st.info(f"開始呼叫爬蟲函數：get_ptt_articles_from_db({st.session_state['board_for_fetch']}, {last_time})")
    
    articles_df = get_ptt_articles_from_db(
        board=st.session_state['board_for_fetch'],
        last_time=last_time
    )
    
    st.info(f"爬蟲函數執行完成，回傳 DataFrame 大小：{len(articles_df)} 行")

    # 如果爬取失敗，嘗試讀取 CSV 備用數據
    if articles_df.empty:
        st.warning("⚠️ 爬取失敗，嘗試讀取 CSV 備用數據...")
        articles_df = load_csv_backup(selected_board)
        
        if not articles_df.empty:
            st.success("✅ 成功使用 CSV 備用數據！")
        else:
            st.error("❌ 爬取失敗且無可用備用數據，請檢查網路連線或提供 CSV 檔案")
            st.session_state['hourly_data_dict'][selected_board] = pd.DataFrame()
            st.session_state['articles_df_dict'][selected_board] = pd.DataFrame()
            st.session_state['trigger_fetch'] = False
            st.stop()

    if not articles_df.empty:
        st.info("開始情感分析...")
        articles_df = analyze_sentiment_batch(articles_df, sentiment_model_placeholder)
        hourly_data = aggregate_emotions_by_hour(articles_df)
        st.session_state['hourly_data_dict'][selected_board] = hourly_data
        st.session_state['articles_df_dict'][selected_board] = articles_df
        save_board_to_sqlite(selected_board, articles_df)  # 寫入 SQLite
        st.success("✅ 文章抓取與情感分析完成！")
        display_analysis_results(selected_board, hourly_data, articles_df,'analyze')
    else:
        st.warning("⚠️ 沒有找到符合條件的文章，請嘗試其他看板或時間範圍。")
        st.session_state['hourly_data_dict'][selected_board] = pd.DataFrame()
        st.session_state['articles_df_dict'][selected_board] = pd.DataFrame()
    st.session_state['trigger_fetch'] = False
elif (
    ('hourly_data_dict' not in st.session_state or selected_board not in st.session_state['hourly_data_dict'] or st.session_state['hourly_data_dict'][selected_board].empty)
    and ('articles_df_dict' not in st.session_state or selected_board not in st.session_state['articles_df_dict'] or st.session_state['articles_df_dict'][selected_board].empty)
    and not st.session_state.get('trigger_fetch', False)
):
    st.info("歡迎使用！請從左側選擇看板，然後點擊「抓取並分析最新文章」按鈕開始。")

st.markdown("---")
st.caption("數據來源：PTT。情感分析結果來自詞典與規則。")