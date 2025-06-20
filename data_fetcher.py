# data_fetcher.py

import streamlit as st
import pandas as pd
import datetime
import requests
from bs4 import BeautifulSoup
import time
import http.cookiejar

# 這裡應該放置你的 PTT 爬蟲和資料庫讀取邏輯
# 為了範例，我們將使用模擬數據

def get_ptt_articles_from_db(board: str, last_time=None) -> pd.DataFrame:
    """
    只抓比 last_time 新的文章，並與 cache 合併去重。
    """
    st.write(f"🔎 正在爬取 PTT {board} 看板過去七天的文章...")
    base_url = "https://www.ptt.cc"
    url = f"https://www.ptt.cc/bbs/{board}/index.html"
    articles = []
    progress_msg = st.empty()
    info_msg = st.empty()
    warning_msg = st.empty()
    error_msg = st.empty()
    
    # 更真實的瀏覽器標頭
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
        'Referer': 'https://www.google.com/'
    })
    
    # 設定更完整的 cookies
    session.cookies.set('over18', '1', domain='www.ptt.cc', path='/')
    session.cookies.set('_ga', 'GA1.1.1234567890.1234567890', domain='.ptt.cc', path='/')
    session.cookies.set('_ga_1234567890', 'GS1.1.1234567890.1.1.1234567890.0.0.0', domain='.ptt.cc', path='/')
    
    days_to_scrape = 7
    today = datetime.date.today()
    start = today - datetime.timedelta(days=days_to_scrape-1)
    max_pages = 20
    request_delay = 3.0  # 增加延遲時間
    page_delay = 2.0     # 增加頁面間延遲
    current_count = 0
    page = 1
    stop_crawling = False
    
    info_msg.info(f"開始爬取，目標日期範圍：{start} ~ {today}")
    info_msg.info(f"目標 URL：{url}")
    
    # 首先訪問 Google，然後再訪問 PTT（模擬真實瀏覽行為）
    try:
        info_msg.info("模擬真實瀏覽行為：先訪問 Google...")
        session.get("https://www.google.com", timeout=10)
        time.sleep(2)
        
        info_msg.info("測試 PTT 連線...")
        test_res = session.get("https://www.ptt.cc/bbs/index.html", timeout=15)
        info_msg.info(f"PTT 主頁連線測試：狀態碼 {test_res.status_code}")
        
        if test_res.status_code == 403:
            error_msg.error("PTT 主頁連線被阻擋（403 Forbidden）")
            info_msg.info("嘗試使用不同的 User-Agent...")
            
            # 嘗試不同的 User-Agent
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
            
            for i, ua in enumerate(user_agents):
                info_msg.info(f"嘗試 User-Agent {i+1}: {ua[:50]}...")
                session.headers.update({'User-Agent': ua})
                time.sleep(3)
                
                try:
                    test_res = session.get("https://www.ptt.cc/bbs/index.html", timeout=15)
                    if test_res.status_code == 200:
                        info_msg.info(f"User-Agent {i+1} 成功！")
                        break
                    else:
                        info_msg.info(f"User-Agent {i+1} 失敗，狀態碼：{test_res.status_code}")
                except Exception as e:
                    info_msg.info(f"User-Agent {i+1} 連線錯誤：{str(e)}")
            
            # 如果所有 User-Agent 都失敗，嘗試直接訪問目標看板
            if test_res.status_code != 200:
                info_msg.info("所有 User-Agent 都失敗，嘗試直接訪問目標看板...")
                try:
                    direct_res = session.get(url, timeout=15)
                    if direct_res.status_code == 200:
                        info_msg.info("直接訪問目標看板成功！")
                    else:
                        error_msg.error(f"直接訪問目標看板也失敗，狀態碼：{direct_res.status_code}")
                        return pd.DataFrame()
                except Exception as e:
                    error_msg.error(f"直接訪問目標看板連線錯誤：{str(e)}")
                    return pd.DataFrame()
        elif test_res.status_code != 200:
            error_msg.error(f"PTT 主頁連線失敗，狀態碼：{test_res.status_code}")
            return pd.DataFrame()
    except Exception as e:
        error_msg.error(f"PTT 主頁連線測試失敗：{str(e)}")
        return pd.DataFrame()
    
    while page <= max_pages and not stop_crawling:
        progress_msg.info(f"正在爬取第 {page} 頁...")
        try:
            info_msg.info(f"正在連接到：{url}")
            res = session.get(url, timeout=15)  # 增加超時時間
            info_msg.info(f"第 {page} 頁連線狀態：{res.status_code}")
            
            if res.status_code == 403:
                error_msg.error("PTT 拒絕連線（403 Forbidden），可能是反爬蟲機制")
                info_msg.info("等待 10 秒後重試...")
                time.sleep(10)
                continue
            elif res.status_code == 404:
                error_msg.error(f"看板 {board} 不存在（404 Not Found）")
                break
            elif res.status_code != 200:
                error_msg.error(f"無法連接到 PTT，狀態碼：{res.status_code}")
                break
                
        except requests.exceptions.Timeout:
            error_msg.error(f"第 {page} 頁連線超時")
            break
        except requests.exceptions.ConnectionError:
            error_msg.error(f"第 {page} 頁連線錯誤")
            break
        except Exception as e:
            error_msg.error(f"第 {page} 頁連線發生未知錯誤：{str(e)}")
            break
            
        # 檢查回應內容
        if len(res.text) < 1000:
            error_msg.error(f"第 {page} 頁回應內容過短，可能被阻擋")
            info_msg.info(f"回應內容長度：{len(res.text)} 字元")
            break
            
        soup = BeautifulSoup(res.text, 'html.parser')
        article_items = soup.select('.r-ent')
        info_msg.info(f"第 {page} 頁解析結果：找到 {len(article_items)} 個 .r-ent 元素")
        
        if not article_items:
            warning_msg.warning(f"第 {page} 頁沒有找到文章列表")
            # 檢查頁面內容，看是否有其他問題
            page_title = soup.find('title')
            if page_title:
                info_msg.info(f"頁面標題：{page_title.text}")
            else:
                info_msg.info("無法找到頁面標題")
            
            # 檢查是否有錯誤訊息
            error_div = soup.find('div', class_='error')
            if error_div:
                info_msg.info(f"頁面錯誤訊息：{error_div.text}")
            break
            
        info_msg.info(f"第 {page} 頁找到 {len(article_items)} 篇文章（最多只爬 {max_pages} 頁）")
        page_has_recent_articles = False
        
        for i, article in enumerate(article_items[:3]):  # 只處理前3篇文章作為測試
            title_element = article.select_one('.title a')
            if not title_element:
                info_msg.info(f"第 {i+1} 篇文章沒有標題連結")
                continue
            title = title_element.text.strip()
            info_msg.info(f"第 {i+1} 篇文章標題：{title}")
            if '[公告]' in title:
                info_msg.info(f"跳過公告文章：{title}")
                continue
            article_url = base_url + title_element['href']
            author = article.select_one('.meta .author').text.strip() if article.select_one('.meta .author') else "未知"
            info_msg.info(f"文章作者：{author}，URL：{article_url}")
            
            # 進入內頁抓發文時間與內文
            time.sleep(request_delay)
            try:
                info_msg.info(f"正在連接到文章內頁：{article_url}")
                art_res = session.get(article_url, timeout=15)
                if art_res.status_code != 200:
                    info_msg.info(f"無法連接到文章內頁，狀態碼：{art_res.status_code}")
                    continue
            except Exception as e:
                info_msg.info(f"連接到文章內頁時發生錯誤：{str(e)}")
                continue
                
            art_soup = BeautifulSoup(art_res.text, 'html.parser')
            meta_elements = art_soup.select('.article-meta-value')
            info_msg.info(f"文章內頁找到 {len(meta_elements)} 個 meta 元素")
            
            if len(meta_elements) >= 4:
                time_str = meta_elements[3].text.strip()
                info_msg.info(f"時間字串：{time_str}")
                try:
                    post_time = datetime.datetime.strptime(time_str, '%a %b %d %H:%M:%S %Y')
                    info_msg.info(f"解析時間成功：{post_time}")
                except:
                    try:
                        post_time = datetime.datetime.strptime(time_str, '%Y/%m/%d %H:%M:%S')
                        info_msg.info(f"解析時間成功（第二種格式）：{post_time}")
                    except:
                        warning_msg.warning(f"無法解析時間格式：{time_str}")
                        continue
            else:
                info_msg.info("文章內頁沒有足夠的 meta 元素")
                continue
                
            if post_time.date() < start:
                info_msg.info(f"遇到舊文章 {title}，時間：{post_time.date()}，停止爬取")
                stop_crawling = True
                break
            if not (start <= post_time.date() <= today):
                info_msg.info(f"文章 {title} 不在目標日期範圍內：{post_time.date()}")
                continue
            if last_time is not None and post_time <= pd.to_datetime(last_time):
                info_msg.info(f"遇到已存在的文章 {title}，時間：{post_time}，停止爬取")
                stop_crawling = True
                break
                
            page_has_recent_articles = True
            info_msg.info(f"文章 {title} 符合條件，開始抓取內文")
            
            # 內文
            main_content = art_soup.select_one('#main-content')
            content = ""
            if main_content:
                content_copy = BeautifulSoup(str(main_content), 'html.parser').select_one('#main-content')
                for push in content_copy.select('.push'):
                    push.decompose()
                content_text = content_copy.text
                signature_pos = content_text.find('--')
                if signature_pos > 0:
                    content_text = content_text[:signature_pos].strip()
                content = content_text
                info_msg.info(f"內文長度：{len(content)} 字元")
            else:
                info_msg.info("無法找到文章內文")
                
            articles.append({
                'timestamp': post_time,
                'content': content,
                'title': title,
                'author': author,
                'board': board
            })
            current_count += 1
            progress_msg.info(f"爬取 {current_count} 篇：{title}")
            
        if not page_has_recent_articles and current_count > 0:
            info_msg.info("本頁沒有符合條件的文章，停止爬取")
            break
        # 翻頁
        prev_page = None
        for link in soup.select('.btn-group-paging a'):
            if '上頁' in link.text:
                prev_page = link
                break
        if prev_page and prev_page.has_attr('href'):
            url = base_url + prev_page['href']
            page += 1
            time.sleep(page_delay)
        else:
            info_msg.info("沒有更多頁面")
            break
    
    # 清除所有進度訊息，只顯示最終結果
    progress_msg.empty()
    info_msg.empty()
    warning_msg.empty()
    error_msg.empty()
    
    if len(articles) > 0:
        st.success(f"✅ 爬取完成！共找到 {len(articles)} 篇符合條件的文章")
    else:
        st.warning("⚠️ 沒有找到符合條件的文章")
    
    # 合併 cache
    if 'articles_df_dict' in st.session_state and board in st.session_state['articles_df_dict'] and not st.session_state['articles_df_dict'][board].empty:
        old_df = st.session_state['articles_df_dict'][board]
        new_df = pd.DataFrame(articles)
        all_df = pd.concat([old_df, new_df], ignore_index=True)
        all_df = all_df.drop_duplicates(subset=['timestamp', 'title', 'author'], keep='last')
        return all_df
    else:
        return pd.DataFrame(articles)