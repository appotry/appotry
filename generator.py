# -*- coding: utf-8 -*-

# author andycrusoe@gmail.com
# Github https://github.com/appotry/
# Blog https://blog.17lai.site
# 参考 https://blog.yuanpei.me/posts/1329254441/
# 2022-05-02

import re
import json
import pytz
import datetime
import requests
from bs4 import BeautifulSoup

headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36'
        }

# 文档实体结构定义
class Post:

    def __init__(self,date,link,title,prefix):
        self.date  = date
        self.link  = link
        self.title = title
        self.prefix = prefix

    def getTitle(self):
        return self.title

    def getLink(self):
        if self.prefix == '' or self.prefix == None:
           return self.link
        else:
            return self.prefix + '/' + self.link

    def getDate(self):
        d = re.findall(r'\d{4}-\d{1,2}-\d{1,2}',self.date)[0]
        t = re.findall(r'\d{2}:\d{2}:\d{2}',self.date)[0]
        dt = '%s %s' % (d,t)
        return datetime.datetime.strptime(dt,'%Y-%m-%d %H:%M:%S')
      
class ReadRss:
 
    def __init__(self, rss_url, headers):
 
        self.url = rss_url
        self.headers = headers
        try:
            response = requests.get(rss_url, headers=self.headers)
            response.encoding = 'utf-8'
            self.r = response
            self.status_code = self.r.status_code
        except Exception as e:
            print('Error fetching the URL: ', rss_url)
            print(e)
        try:    
            self.soup = BeautifulSoup(self.r.text, 'lxml')
        except Exception as e:
            print('Could not parse the xml: ', self.url)
            print(e)
        self.articles = self.soup.findAll('item')
        self.articles_dicts = [{'title':a.find('title').text,'link':a.link.next_sibling.replace('\n','').replace('\t',''),'description':a.find('description').text,'pubdate':a.find('pubdate').text} for a in self.articles]
        self.urls = [d['link'] for d in self.articles_dicts if 'link' in d]
        self.titles = [d['title'] for d in self.articles_dicts if 'title' in d]
        self.descriptions = [d['description'] for d in self.articles_dicts if 'description' in d]
        self.pub_dates = [d['pubdate'] for d in self.articles_dicts if 'pubdate' in d]

def loadPostsByRSS():
    feed = ReadRss(POSTS_RSS_URL, headers)
    # print(feed.urls)
    if feed.status_code == 200:
        for i in range(RECENT_POST_LIMIT):
            publish_date = datetime.datetime.strptime(feed.pub_dates[i], '%a, %d %b %Y %H:%M:%S +0800')
            publish_date = datetime.datetime.strftime(publish_date,'%Y-%m-%d %H:%M:%S')
            yield Post(publish_date,feed.urls[i],feed.titles[i], None)
    else:
        return []

# 常量定义
POSTS_RSS_URL = 'https://blog.17lai.site/rss.xml'

TO_REPLACE_POSTS = '{{Recent Posts}}'
TO_REPLACE_DATE = '{{Generated At}}'

BLOG_URL_PREFIX = 'https://blog.17lai.site'

RECENT_POST_LIMIT = 12

# 时区定义
tz = pytz.timezone('Asia/Shanghai')

def formatPost(item):
    itemTpl = '* {0} - [{1}]({2})'
    return itemTpl.format(
        datetime.datetime.strftime(item.getDate(),'%Y-%m-%d'),
        item.getTitle(),
        item.getLink()
    )

if __name__ == '__main__':
    # print(feed.urls)
    with open('./README.md', 'wt', encoding='utf-8') as fw:
        with open('./.template/README.md', 'rt', encoding='utf-8') as fr:
            posts = sorted(loadPostsByRSS(), key=lambda x:x.getDate(),reverse=True)
            recent_posts = ''
            if len(posts) > 0:
                recent_posts = '\n'.join(list(map(lambda x: formatPost(x), posts[:RECENT_POST_LIMIT])))
            content = fr.read().replace(TO_REPLACE_POSTS, recent_posts)
            createdAt = datetime.datetime.now(tz)
            createdAt = datetime.datetime.strftime(createdAt,'%Y-%m-%d %H:%M:%S')
            content = content.replace(TO_REPLACE_DATE, createdAt)
            fw.write(content)
