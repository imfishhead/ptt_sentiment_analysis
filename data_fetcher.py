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
        'User-Agent': 'Mozilla/5.0',
        'Accept-Language': 'zh-TW,zh;q=0.9',
        'Referer': 'https://www.ptt.cc/bbs/index.html'
    })
    days_to_scrape = 7
    today = datetime.date.today()
    start = today - datetime.timedelta(days=days_to_scrape-1)
    max_pages = 200
    request_delay = 1.0
    page_delay = 0.5
    current_count = 0
    page = 1
    stop_crawling = False
    while page <= max_pages and not stop_crawling:
        res = session.get(url)
        if res.status_code != 200:
            break
        soup = BeautifulSoup(res.text, 'html.parser')
        article_items = soup.select('.r-ent')
        if not article_items:
            break
        page_has_recent_articles = False
        for article in article_items:
            title_element = article.select_one('.title a')
            if not title_element:
                continue
            title = title_element.text.strip()
            if '[公告]' in title:
                continue
            article_url = base_url + title_element['href']
            author = article.select_one('.meta .author').text.strip() if article.select_one('.meta .author') else "未知"
            # 進入內頁抓發文時間與內文
            time.sleep(request_delay)
            art_res = session.get(article_url)
            if art_res.status_code != 200:
                continue
            art_soup = BeautifulSoup(art_res.text, 'html.parser')
            meta_elements = art_soup.select('.article-meta-value')
            if len(meta_elements) >= 4:
                time_str = meta_elements[3].text.strip()
                try:
                    post_time = datetime.datetime.strptime(time_str, '%a %b %d %H:%M:%S %Y')
                except:
                    try:
                        post_time = datetime.datetime.strptime(time_str, '%Y/%m/%d %H:%M:%S')
                    except:
                        continue
            else:
                continue
            if not (start <= post_time.date() <= today):
                continue
            if last_time is not None and post_time <= pd.to_datetime(last_time):
                stop_crawling = True
                break
            page_has_recent_articles = True
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
            articles.append({
                'timestamp': post_time,
                'content': content,
                'title': title,
                'author': author,
                'board': board
            })
            current_count += 1
            progress_msg.info(f"爬取 {current_count} 篇…")
        if not page_has_recent_articles and current_count > 0:
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
            break
    # 合併 cache
    if 'articles_df' in st.session_state and not st.session_state['articles_df'].empty:
        old_df = st.session_state['articles_df']
        new_df = pd.DataFrame(articles)
        all_df = pd.concat([old_df, new_df], ignore_index=True)
        all_df = all_df.drop_duplicates(subset=['timestamp', 'title', 'author'], keep='last')
        return all_df
    else:
        return pd.DataFrame(articles)