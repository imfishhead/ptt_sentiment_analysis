import streamlit as st
import pandas as pd
import numpy as np
from snownlp import SnowNLP # 導入 SnowNLP
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm # 用於設置中文字體
import seaborn as sns # 用於熱力圖

# --- 情感詞典和相關配置 ---
emotion_lexicon = {
    "joy": ["開心", "高興", "愉快", "喜悅", "快樂", "興奮", "歡喜", "欣慰", "歡樂", "幸福", "欣喜", "滿足",
             "美好", "享受", "愜意", "舒暢", "樂觀", "愉悅", "笑", "歡笑", "微笑", "興高采烈", "眉飛色舞"],

    "sadness": ["悲傷", "難過", "傷心", "哀痛", "憂愁", "痛苦", "悲痛", "哀傷", "悲哀", "憂鬱", "沮喪", "失落",
                 "消沉", "哭", "淚", "嘆息", "心酸", "惋惜", "遺憾", "失望", "無奈", "苦惱", "憂傷", "低落"],

    "anger": ["憤怒", "生氣", "惱火", "氣憤", "火大", "怒氣", "暴怒", "發火", "憤恨", "怨恨", "惱怒", "不滿",
               "不爽", "不快", "不悅", "煩躁", "惱人", "可惡", "討厭", "煩人", "忿忿不平", "義憤", "怒髮沖冠"],

    "fear": ["恐懼", "害怕", "擔憂", "恐慌", "驚恐", "憂慮", "焦慮", "緊張", "懼怕", "畏懼", "膽怯", "提心吊膽",
              "擔心", "怕", "憂心", "不安", "戰戰兢兢", "心驚肉跳", "惶恐", "危險", "威脅", "戰慄", "畏縮"],

    "surprise": ["驚訝", "驚奇", "驚喜", "意外", "震驚", "吃驚", "詫異", "驚嘆", "難以置信", "目瞪口呆", "大吃一驚",
                  "出乎意料", "沒想到", "不可思議", "嚇一跳", "愕然", "錯愕", "驚詫", "驚愕", "出人意料"],

    "disgust": ["厭惡", "噁心", "反感", "嫌棄", "排斥", "鄙視", "蔑視", "嫌惡", "討厭", "憎恨", "憎惡", "不屑",
                 "輕蔑", "唾棄", "看不起", "瞧不起", "齟齬", "作嘔", "不堪入目", "惡劣", "不齒", "痛恨"],

    "anticipation": ["期待", "希望", "盼望", "憧憬", "展望", "向往", "渴望", "企盼", "嚮往", "預期", "等待",
                      "期盼", "指望", "冀望", "預測", "預感", "預想", "預見", "盼", "迫不及待"],

    "trust": ["信任", "信賴", "相信", "信心", "確信", "依賴", "依靠", "信念", "忠誠", "忠實", "真誠", "可靠",
               "坦率", "坦誠", "誠實", "誠懇", "誠意", "坦白", "篤定", "肯定", "篤信", "堅信"]
}

negation_words = ["不", "沒", "無", "非", "別", "莫", "勿", "毫無", "不要", "不能", "不可", "不必", "未", "反"]

degree_adverbs = {
    "extreme": ["極其", "極度", "極為", "極端", "極", "非常", "十分", "萬分", "極為", "異常", "格外", "超級", "頂級",
               "最為", "無比", "最", "至極", "極致", "史無前例", "絕對", "徹底", "完全", "全然"],
    "high": ["很", "太", "特別", "相當", "尤其", "越發", "更加", "更為", "更", "挺", "蠻", "頗", "尤為",
            "不少", "不小", "不乏", "甚", "甚為", "特", "之極", "分外"],
    "moderate": ["比較", "較為", "略為", "略微", "略", "稍微", "稍稍", "稍", "稍許", "有點", "有些", "有一點",
               "多少", "幾分"],
    "low": ["一點點", "一絲", "一毫", "微微", "略微"]
}

emotion_colors = {
    "joy": "#FFCC00", "sadness": "#3333FF", "anger": "#FF3333", "fear": "#9900CC",
    "surprise": "#33CCFF", "disgust": "#669900", "anticipation": "#FF9933",
    "trust": "#33CC33", "neutral": "#999999"
}

emotion_names_zh = {
    "joy": "喜悅", "sadness": "悲傷", "anger": "憤怒", "fear": "恐懼",
    "surprise": "驚奇", "disgust": "厭惡", "anticipation": "期待", "trust": "信任",
    "neutral": "中性"
}

emotion_emojis = {
    "joy": "😄", "sadness": "😢", "anger": "😠", "fear": "😨",
    "surprise": "😲", "disgust": "🤢", "anticipation": "🙂", "trust": "🤝",
    "neutral": "😐"
}

emotion_coordinates = {
    "joy": (0.8, 0.6), "sadness": (-0.7, -0.6), "anger": (-0.6, 0.8), "fear": (-0.7, 0.7),
    "surprise": (0.4, 0.8), "disgust": (-0.8, 0.1), "anticipation": (0.5, 0.4),
    "trust": (0.7, -0.2), "neutral": (0.0, 0.0)
}

# --- 輔助函數 ---

def split_paragraphs(text):
    """將文本分割成段落"""
    # 簡單地按換行符分割，可以根據需要調整
    return text.split('\n\n')

def setup_chinese_display():
    """設置 Matplotlib 中文字體顯示"""
    font_paths = fm.findSystemFonts(fontpaths=None, fontext='ttf')
    chinese_fonts = [f for f in font_paths if 'kai' in f.lower() or 'hei' in f.lower() or 'msyh' in f.lower()]
    
    if chinese_fonts:
        for font_path in chinese_fonts:
            if 'msyh' in font_path.lower():
                plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
                break
            elif 'kai' in font_path.lower():
                 plt.rcParams['font.sans-serif'] = ['KaiTi']
                 break
            elif 'hei' in font_path.lower():
                 plt.rcParams['font.sans-serif'] = ['SimHei']
                 break
        else:
            plt.rcParams['font.sans-serif'] = [fm.FontProperties(fname=chinese_fonts[0]).get_name()]
        
        plt.rcParams['axes.unicode_minus'] = False
        return plt.rcParams['font.sans-serif'][0]
    else:
        st.warning("⚠️ 未找到系統中文字體，圖表中的中文可能無法正常顯示。請確保您的系統已安裝中文字體。")
        return None

# 調整 analyze_article_sentiment 使其適合 Streamlit 的情感分析流程
def analyze_article_sentiment(text):
    """
    分析文章的情感流動 (基於 SnowNLP 極性)

    參數:
        text: 要分析的文本

    返回:
        avg_sentiment: 文本的平均情感得分 (0-1，越高越正面)
    """
    if not text.strip():
        return 0.5

    s = SnowNLP(text)
    return s.sentiments

# 核心情感分析邏輯
def analyze_emotion_types(text: str, emotion_lexicon: dict, negation_words: list, degree_adverbs: dict) -> dict:
    """
    根據情感詞典和規則分析文本中的八項情感類型。

    參數:
        text: 要分析的文本
        emotion_lexicon: 情感詞典
        negation_words: 否定詞列表
        degree_adverbs: 程度副詞列表

    返回:
        包含各情感類型分數的字典 (0-1，歸一化)。
    """
    overall_emotion_scores = {emotion_type: 0 for emotion_type in emotion_lexicon.keys()}
    total_words_processed = 0

    s = SnowNLP(text)
    words = s.words

    for i, word in enumerate(words):
        is_negated = False
        if i > 0 and words[i-1] in negation_words:
            is_negated = True
        
        degree_multiplier = 1.0
        for offset in [1, 2]:
            if i - offset >= 0:
                prev_word = words[i - offset]
                for level, adverbs in degree_adverbs.items():
                    if prev_word in adverbs:
                        if level == "extreme":
                            degree_multiplier = 2.0
                        elif level == "high":
                            degree_multiplier = 1.5
                        elif level == "moderate":
                            degree_multiplier = 1.0
                        elif level == "low":
                            degree_multiplier = 0.5
                        break
                if degree_multiplier != 1.0:
                    break

        for emotion_type, emotion_words in emotion_lexicon.items():
            if word in emotion_words:
                score = 1 * degree_multiplier
                if is_negated:
                    if emotion_type == "joy":
                        overall_emotion_scores["sadness"] += score
                    elif emotion_type == "trust":
                        overall_emotion_scores["disgust"] += score
                    elif emotion_type == "anticipation":
                        overall_emotion_scores["fear"] += score
                    elif emotion_type == "sadness":
                        overall_emotion_scores["joy"] += score
                    elif emotion_type == "fear":
                        overall_emotion_scores["trust"] += score
                    elif emotion_type == "disgust":
                        overall_emotion_scores["joy"] += score
                    
                    overall_emotion_scores[emotion_type] -= score
                else:
                    overall_emotion_scores[emotion_type] += score
                total_words_processed += 1

    # 歸一化分數到 0-1 範圍
    # 假設一篇短文最多一種情感詞可能出現 5 次，且程度副詞加乘 2x。
    # 因此最大理想分數可能為 1 * 5 * 2 = 10。
    # 這裡設定一個經驗值 MAX_EMOTION_SCORE_EXPECTED 來歸一化。
    MAX_EMOTION_SCORE_EXPECTED = 5.0 # 這個值可以根據你的文章長度、情感詞密度來調整

    for emo_type in overall_emotion_scores:
        overall_emotion_scores[emo_type] = np.clip(overall_emotion_scores[emo_type], 0, MAX_EMOTION_SCORE_EXPECTED) / MAX_EMOTION_SCORE_EXPECTED

    if total_words_processed == 0:
        for emo_type in overall_emotion_scores:
            overall_emotion_scores[emo_type] = 0.0

    return overall_emotion_scores

# Streamlit 應用程序將會調用這個函數
def get_sentiment_model():
    """
    這個函數在這裡只是為了兼容 app.py 的接口，
    實際上不載入任何模型，因為情感分析是基於詞典和規則。
    """
    return "dictionary_based_model" # 返回一個標誌，表示已準備好

def analyze_sentiment_batch(df: pd.DataFrame, model_placeholder) -> pd.DataFrame:
    """
    對 DataFrame 中的文章內容進行情感分析，並將八項情感分數加入到 DataFrame 中。
    此函數現在使用基於詞典的分析方法。
    """
    if df.empty:
        return df

    st.write("✨ 正在使用詞典和規則進行情感分析...")
    
    from config import EMOTIONS_NAMES # 從 config 導入情感名稱

    for emo in EMOTIONS_NAMES:
        df[emo] = 0.0

    progress_text = "情感分析進度："
    my_bar = st.progress(0, text=progress_text)

    for i, row in df.iterrows():
        text = row['content']
        emotion_scores = analyze_emotion_types(text, emotion_lexicon, negation_words, degree_adverbs)
        
        for emo in EMOTIONS_NAMES:
            df.loc[i, emo] = emotion_scores.get(emo, 0.0)

        my_bar.progress((i + 1) / len(df), text=progress_text + f"{i+1}/{len(df)} 條文章")
    
    my_bar.empty()

    st.write("✅ 情感分析完成。")
    return df

# 注意：visualize_sentiment_flow 和 annotate_text_sentiment 函數
# 由於其輸出的圖表類型和 HTML 渲染方式與 Streamlit 的集成有所不同，
# 在 Streamlit app.py 中直接調用可能會遇到問題。
# Streamlit 推薦使用 st.pyplot() 和 st.markdown(unsafe_allow_html=True) 來顯示。
# 這裡暫時保留這些函數，但它們不會被 app.py 直接調用，除非你調整 app.py。
# 如果需要，可以將這些可視化邏輯移植到 app.py 中，並使用 Streamlit 的對應函數。