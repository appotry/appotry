# -*- coding: utf-8 -*-

# author andycrusoe@gmail.com
# Github https://github.com/appotry/
# Blog https://blog.17lai.site
# 参考 https://blog.yuanpei.me/posts/1329254441/
# 2022-05-02 (Updated 2025 for Cloudscraper)

import re
import pytz
import datetime
import cloudscraper
from bs4 import BeautifulSoup

# 文档实体结构定义
class Post:
    def __init__(self, date, link, title, prefix):
        self.date = date
        self.link = link
        self.title = title
        self.prefix = prefix

    def getTitle(self):
        return self.title

    def getLink(self):
        if self.prefix == '' or self.prefix is None:
            return self.link
        else:
            return self.prefix + '/' + self.link

    def getDate(self):
        # 提取日期和时间
        d_match = re.findall(r'\d{4}-\d{1,2}-\d{1,2}', self.date)
        t_match = re.findall(r'\d{2}:\d{2}:\d{2}', self.date)
        
        if d_match and t_match:
            d = d_match[0]
            t = t_match[0]
            dt = '%s %s' % (d, t)
            return datetime.datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
        else:
            # 如果匹配失败，返回当前时间防止报错
            return datetime.datetime.now()

class ReadRss:
    def __init__(self, rss_url):
        self.url = rss_url
        self.page_source = None
        self.articles = []
        self.urls = []
        self.titles = []
        self.pub_dates = []
        
        # --- 核心修改：使用 Cloudscraper ---
        try:
            # 创建 scraper 实例，模拟 Chrome 浏览器
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'desktop': True
                }
            )
            print(f'Starting to fetch RSS from {rss_url} using Cloudscraper...')
            response = scraper.get(rss_url)
            
            if response.status_code == 200:
                self.page_source = response.text
                print(f'Request to {rss_url} successful')
            else:
                print(f'Error: Status code {response.status_code}')
                return # 提前结束

        except Exception as e:
            print('Error fetching the URL with Cloudscraper: ', rss_url)
            print(e)
            return

        # --- 解析逻辑 (保持原有 BeautifulSoup 方式) ---
        try:
            if self.page_source:
                # 使用 xml 解析器
                self.soup = BeautifulSoup(self.page_source, 'xml') 
                # 查找所有 item 标签
                self.articles = self.soup.find_all('item')
                
                self.articles_dicts = []
                for a in self.articles:
                    # 更加健壮的获取方式，防止某些标签缺失导致报错
                    title_tag = a.find('title')
                    link_tag = a.find('link')
                    desc_tag = a.find('description')
                    date_tag = a.find('pubDate') # 注意：XML通常是 pubDate 大小写敏感，这里做了兼容

                    item_data = {
                        'title': title_tag.text if title_tag else 'No Title',
                        'link': link_tag.text if link_tag else '',
                        'description': desc_tag.text if desc_tag else '',
                        'pubdate': date_tag.text if date_tag else ''
                    }
                    self.articles_dicts.append(item_data)

                self.urls = [d['link'] for d in self.articles_dicts]
                self.titles = [d['title'] for d in self.articles_dicts]
                self.pub_dates = [d['pubdate'] for d in self.articles_dicts]
                
                print(f'Parsed {len(self.articles)} articles from RSS feed')
        except Exception as e:
            print('Could not parse the xml: ', self.url)
            print(e)

def loadPostsByRSS():
    # 优先使用受 Cloudflare 保护的地址进行测试
    target_url = POSTS_RSS_URL 
    
    feed = ReadRss(target_url)
    
    if feed.page_source and feed.pub_dates:
        count = min(RECENT_POST_LIMIT, len(feed.pub_dates))
        for i in range(count):
            try:
                raw_date = feed.pub_dates[i]
                # 处理日期格式: RSS 标准格式通常是 "Tue, 02 May 2023 10:00:00 +0800"
                # 原代码格式适配
                try:
                    publish_date_obj = datetime.datetime.strptime(raw_date, '%a, %d %b %Y %H:%M:%S +0800')
                except ValueError:
                    # 备用格式尝试：有时候时区可能是 GMT 或其他
                    # 如果依然失败，建议引入 dateutil.parser
                    try: 
                         publish_date_obj = datetime.datetime.strptime(raw_date, '%a, %d %b %Y %H:%M:%S GMT')
                    except:
                        # 如果还是解析失败，暂时跳过这个日期处理，避免程序崩溃
                        print(f"Warning: Date format not recognized for {raw_date}")
                        continue

                publish_date_str = datetime.datetime.strftime(publish_date_obj, '%Y-%m-%d %H:%M:%S')
                
                yield Post(publish_date_str, feed.urls[i], feed.titles[i], None)
            except Exception as e:
                print(f'Error processing article {i}: {e}')
    else:
        print('Error: could not retrieve page source or no articles found')
        return []

# --- 配置常量 ---

# 目标 RSS 地址 (Cloudflare 保护)
POSTS_RSS_URL = 'https://blog.17lai.site/rss.xml' 
# 备用地址 (如果不通可以切换测试)
# POSTS_RSS_URL = 'https://17lai.vercel.app/rss.xml'

TO_REPLACE_POSTS = '{{Recent Posts}}'
TO_REPLACE_DATE = '{{Generated At}}'
RECENT_POST_LIMIT = 12

# 时区定义
tz = pytz.timezone('Asia/Shanghai')

def formatPost(item):
    itemTpl = '* {0} - [{1}]({2})'
    # 简单的异常处理，防止 item.getDate() 出错
    try:
        date_str = datetime.datetime.strftime(item.getDate(), '%Y-%m-%d')
    except:
        date_str = "Unknown Date"
        
    return itemTpl.format(
        date_str,
        item.getTitle(),
        item.getLink()
    )

if __name__ == '__main__':
    print("Starting generator...")
    
    # 读取模板
    template_path = './.template/README.md'
    readme_path = './README.md'
    
    try:
        with open(template_path, 'rt', encoding='utf-8') as fr:
            template_content = fr.read()
            
        # 获取文章并排序
        posts_generator = loadPostsByRSS()
        posts = sorted(posts_generator, key=lambda x: x.getDate(), reverse=True)
        
        recent_posts = ''
        if len(posts) > 0:
            recent_posts = '\n'.join(list(map(lambda x: formatPost(x), posts[:RECENT_POST_LIMIT])))
            print(f"Generated {len(posts)} posts.")
        else:
            print("No posts found to update.")

        # 替换内容
        content = template_content.replace(TO_REPLACE_POSTS, recent_posts)
        
        # 替换生成时间
        createdAt = datetime.datetime.now(tz)
        createdAtStr = datetime.datetime.strftime(createdAt, '%Y-%m-%d %H:%M:%S')
        content = content.replace(TO_REPLACE_DATE, createdAtStr)
        
        # 写入 README
        with open(readme_path, 'wt', encoding='utf-8') as fw:
            fw.write(content)
            
        print("README.md updated successfully.")
        
    except FileNotFoundError as e:
        print(f"File not found error: {e}")
        print(f"Please ensure {template_path} exists.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")