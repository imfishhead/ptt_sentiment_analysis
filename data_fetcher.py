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
    session = requests.Session()
    cookies = http.cookiejar.CookieJar()
    cookie = http.cookiejar.Cookie(
        version=0, name='over18', value='1',
        port=None, port_specified=False,
        domain='www.ptt.cc', domain_specified=False,
        domain_initial_dot=False,
        path='/', path_specified=True,
        secure=False, expires=None,
        discard=True, comment=None,
        comment_url=None, rest={'HttpOnly': None},
        rfc2109=False
    )
    cookies.set_cookie(cookie)
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
        'Referer': 'https://www.ptt.cc/bbs/index.html',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    })
    days_to_scrape = 7
    today = datetime.date.today()
    start = today - datetime.timedelta(days=days_to_scrape-1)
    max_pages = 20
    request_delay = 1.0
    page_delay = 0.5
    current_count = 0
    page = 1
    stop_crawling = False
    
    info_msg.info(f"開始爬取，目標日期範圍：{start} ~ {today}")
    info_msg.info(f"目標 URL：{url}")
    
    while page <= max_pages and not stop_crawling:
        progress_msg.info(f"正在爬取第 {page} 頁...")
        try:
            res = session.get(url, timeout=10)
            info_msg.info(f"第 {page} 頁連線狀態：{res.status_code}")
            if res.status_code != 200:
                error_msg.error(f"無法連接到 PTT，狀態碼：{res.status_code}")
                break
        except Exception as e:
            error_msg.error(f"連線錯誤：{str(e)}")
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
            break
            
        info_msg.info(f"第 {page} 頁找到 {len(article_items)} 篇文章（最多只爬 {max_pages} 頁）")
        page_has_recent_articles = False
        
        for i, article in enumerate(article_items[:5]):  # 只處理前5篇文章作為測試
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
                art_res = session.get(article_url, timeout=10)
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