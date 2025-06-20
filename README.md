# 📊 PTT 看板情感趨勢分析儀

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

一個基於 Streamlit 的 PTT 看板情感分析工具，能夠即時爬取 PTT 文章並進行八維情感分析，提供互動式的情感趨勢視覺化。

## 🌟 主要功能

### 📈 情感分析
- **八維情感分析**：基於 Plutchik 情感輪理論，分析喜悅、悲傷、憤怒、恐懼、驚奇、厭惡、期待、信任等八種情感
- **即時情感趨勢**：每小時聚合情感數據，掌握社群情感波動
- **互動式雷達圖**：動態顯示選定時間點的情感分佈
- **詞典式分析**：使用自定義中文情感詞典，支援否定詞和程度副詞處理

### 🕷️ 爬蟲
- **增量爬取**：只抓取新文章，避免重複處理
- **反爬蟲繞過**：多種 User-Agent 輪換、真實瀏覽行為模擬
- **多看板支援**：支援 Gossiping、WomenTalk、Tech_Job、Boy-Girl、Stock、NBA 等熱門看板
- **進度顯示**：即時顯示爬取進度和狀態

### 💾 數據管理
- **SQLite 快取**：持久化儲存文章數據，支援跨會話使用
- **自動去重**：基於時間戳、標題、作者進行去重處理
- **數據匯出**：支援 CSV 格式下載情感分析結果
- **記憶體優化**：延遲載入，避免記憶體溢出

### 🎨 使用者介面
- **響應式設計**：支援各種螢幕尺寸
- **直觀操作**：簡單的側邊欄控制，一鍵開始分析
- **即時反饋**：詳細的進度訊息和錯誤提示
- **美觀視覺化**：使用 Plotly 製作互動式圖表

## 🚀 快速開始

### 環境需求
- Python 3.10
- 網路連線（用於爬取 PTT 文章）

### 安裝步驟

1. **安裝必要套件**
```bash
pip install -r requirements.txt
```

2. **啟動應用**
```bash
streamlit run app.py
```

3. **開啟瀏覽器**
應用將在 `http://localhost:8501` 啟動

## 📖 使用指南

### 基本操作
1. **選擇看板**：在側邊欄選擇想要分析的 PTT 看板
2. **查看快取**：系統會顯示目前快取的文章數量
3. **開始分析**：點擊「抓取並分析最新文章」按鈕
4. **查看結果**：等待分析完成，查看情感趨勢圖表和數據

### 功能說明

#### 情感趨勢時間軸
- 使用滑桿選擇特定時間點
- 查看該時間點的情感分佈
- 支援過去七天的數據範圍

#### 情感八角向量圖
- 互動式雷達圖顯示八種情感強度
- 即時更新選定時間點的數據
- 支援全螢幕顯示

#### 數據表格
- 顯示每小時的情感分數
- 支援排序和篩選
- 可下載為 CSV 格式

## 🏗️ 專案結構

```
ptt_sentiment_analysis/
├── app.py                 # 主應用程式（Streamlit 介面）
├── data_fetcher.py        # PTT 爬蟲模組
├── sentiment_analyzer.py  # 情感分析引擎
├── config.py             # 配置檔案
├── requirements.txt      # Python 依賴
├── ptt_cache.db         # SQLite 快取資料庫
└── README.md            # 專案說明文件
```

## 🔧 技術架構

### 後端技術
- **Streamlit**：Web 應用框架
- **Pandas**：數據處理和分析
- **Plotly**：互動式視覺化
- **SQLite**：本地數據儲存
- **Requests + BeautifulSoup**：網頁爬蟲
- **SnowNLP**：中文自然語言處理

### 情感分析算法
- **詞典式分析**：基於自定義中文情感詞典
- **否定詞處理**：支援「不」、「沒」、「無」等否定詞
- **程度副詞**：支援「很」、「非常」、「極其」等程度詞
- **情感映射**：否定詞會將情感轉換為對立情感

### 爬蟲策略
- **多 User-Agent 輪換**：避免被反爬蟲機制偵測
- **真實瀏覽行為模擬**：先訪問 Google 再訪問 PTT
- **延遲機制**：隨機延遲避免過於頻繁的請求
- **錯誤重試**：遇到 403 錯誤時自動重試

## 🌐 部署指南

### Render 部署
1. 在 Render 創建新的 Web Service
2. 連接 GitHub 倉庫
3. 設定環境變數（如需要）
4. 部署完成後即可使用

### 本地部署
```bash
# development
streamlit run app.py --server.port 8501

# production
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

## ⚠️ 注意事項

### 使用限制
- **PTT 反爬蟲**：PTT 有反爬蟲機制，可能導致某些請求被阻擋
- **資料來源**：僅供學術研究使用，請遵守 PTT 使用條款
- **更新頻率**：建議不要過於頻繁地爬取，避免對 PTT 造成負擔

### 技術限制
- **記憶體使用**：大量文章可能消耗較多記憶體
- **網路連線**：需要穩定的網路連線進行爬取
- **處理速度**：情感分析需要一定時間，請耐心等待

## 🤝 貢獻指南

歡迎提交 Issue 和 Pull Request！

### 開發環境設定
1. Fork 專案
2. 創建功能分支：`git checkout -b feature/AmazingFeature`
3. 提交變更：`git commit -m 'Add some AmazingFeature'`
4. 推送分支：`git push origin feature/AmazingFeature`
5. 開啟 Pull Request

## 📄 授權條款

本專案採用 MIT 授權條款 - 詳見 [LICENSE](LICENSE) 文件

## 🙏 致謝

- **PTT**：提供豐富的社群討論內容
- **Streamlit**：優秀的 Web 應用框架
- **SnowNLP**：中文自然語言處理工具
- **Plotly**：互動式視覺化庫

## 📞 聯絡資訊

如有問題或建議，請透過以下方式聯絡：

- 📧 Email：your.email@example.com
- 🐛 Issues：[GitHub Issues](https://github.com/imfishhead/ptt_sentiment_analysis/issues)
- 📖 Wiki：[專案 Wiki](https://github.com/imfishhead/ptt_sentiment_analysis/wiki)

---

⭐ 如果這個專案對你有幫助，請給我們一個 Star！ 