# coding: utf-8

from __future__ import unicode_literals

import HTMLParser
import re
import os
import sys
import json
import random
import datetime
import redis
import scrapy
import logging

from scrapy import Request
from scrapy.exceptions import CloseSpider
from wechat_sender import LoggingSenderHandler
from Shadow.items import ZHArticleItem, ZHCombinationItem, TagItem, ZHColumnItem, ZHUserItem, ColumnItem
from lg_data.db.models import DBSession, ZHRandomColumn
from Shadow.utils import md5

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.append(BASE_DIR)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('scrapy')
log_formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
sender_logger = LoggingSenderHandler('spider', 'rapospectre', 'Sender 信息群', 'http://114.215.153.187',
                                     level=logging.ERROR)
sender_logger.setFormatter(log_formatter)
file_hdlr = logging.FileHandler('/var/log/scrapy/spider_{0:%Y-%m-%d}.log'.format(datetime.datetime.now()), 'a')
file_hdlr.setLevel(logging.INFO)
file_hdlr.setFormatter(log_formatter)
logger.addHandler(sender_logger)
logger.addHandler(file_hdlr)


class ZhuanLanArticleSpider(scrapy.Spider):
    name = 'zlarticle'
    host = 'https://zhuanlan.zhihu.com/'
    start_urls = ['https://zhuanlan.zhihu.com/p/27143205']
    column_api_url = 'https://zhuanlan.zhihu.com/api/columns/{slug}'
    response = None
    headers = {}

    custom_settings = {
        'ITEM_PIPELINES': {
            # 'Shadow.pipelines.CheckAvailablePipeline': 200,
            'Shadow.pipelines.ArticleDataStorePipeline': 300,
        },
        'DOWNLOADER_MIDDLEWARES': {
            'Shadow.middlewares.UserAgentMiddleware': 1,
            # 'Shadow.middlewares.ProxyMiddleware': 2,

        },
        'COOKIES_ENABLED': False,
    }

    def get_client_config(self):
        matchs = re.findall(r'<textarea id="clientConfig" hidden="">(.*?)</textarea>', self.response.body)
        html_parser = HTMLParser.HTMLParser()
        unescape_data = html_parser.unescape(matchs[0])
        data = json.loads(unescape_data)
        return data

    def generate_header(self):
        data = self.get_client_config()
        tokens = data.get('tokens')
        headers = self.response.headers
        headers['referer'] = self.response.url
        headers['authorization'] = tokens.get('Authorization')
        headers['x-xsrf-token'] = tokens.get('X-XSRF-TOKEN')
        self.headers = headers
        return self.headers

    def parse_column_info(self, response):
        data = json.loads(response.body)
        item = response.meta['item']
        slug = data.get('slug')
        item.column['name'] = data.get('name')
        item.column['link'] = 'https://zhuanlan.zhihu.com/{0}'.format(slug)
        item.column['hash'] = md5('{0}'.format(slug))
        item.column['slug'] = slug
        item.column['description'] = data.get('description')
        item.column['avatar'] = data.get('avatar').get('template',
                                                       'https://pic2.zhimg.com/{id}_{size}.jpg').format(
            id=data.get('avatar').get('id'), size='l')
        creator = data.get('creator')
        if creator:
            item.creator['zuid'] = creator.get('uid')
            item.creator['name'] = creator.get('name')
            item.creator['link'] = creator.get('profileUrl')
            item.creator['hash'] = creator.get('hash')
            item.creator['slug'] = creator.get('slug')
            item.creator['description'] = creator.get('description')
            item.creator['headline'] = creator.get('bio')
            item.creator['avatar'] = creator.get('avatar').get('template',
                                                               'https://pic1.zhimg.com/{id}_{size}.jpg').format(
                id=creator.get('avatar').get('id'), size='l')
        else:
            item.creator = item.author
        return item

    def parse(self, response):
        self.response = response
        matchs = re.findall(r'<textarea id="preloadedState" hidden="">(.*?)</textarea>', response.body)
        html_parser = HTMLParser.HTMLParser()
        unescape_data = html_parser.unescape(matchs[0].decode('utf-8'))
        a = re.findall(r'"updated":(.*?),"canComment"', unescape_data)
        unescape_data = unescape_data.replace(a[0], '" "')
        data = json.loads(unescape_data)
        item = ZHCombinationItem()
        article_data = data.get('database').get('Post').values()[0]
        author = article_data.get('author', None)
        column = article_data.get('column', {}).get('slug', None)
        link = 'https://zhuanlan.zhihu.com/p/{0}'.format(article_data.get('slug'))
        item.article['title'] = article_data.get('title')
        item.article['content'] = article_data.get('content')
        item.article['summary'] = article_data.get('summary')
        item.article['cover'] = article_data.get('titleImage')
        item.article['token'] = article_data.get('slug')
        item.article['md5'] = md5('{0}'.format(item.article['token']))
        item.article['link'] = link
        item.article['create_time'] = article_data.get('publishedTime')
        item.article['modify_time'] = article_data.get('publishedTime')
        if author:
            author_data = data.get('database').get('User').get(author)
            item.author['zuid'] = author_data.get('uid')
            item.author['name'] = author_data.get('name')
            item.author['link'] = author_data.get('profileUrl')
            item.author['hash'] = author_data.get('hash')
            item.author['slug'] = author_data.get('slug')
            item.author['description'] = author_data.get('description')
            item.author['headline'] = author_data.get('headline')
            item.author['avatar'] = author_data.get('avatarUrl')
        topics = article_data.get('topics')
        for topic in topics:
            tp = TagItem()
            tp['name'] = topic.get('name')
            item.tags.append(tp)

        if column:
            url = self.column_api_url.format(slug=column)
            request = Request(url, headers=self.generate_header(), callback=self.parse_column_info)
            request.meta['item'] = item
            return request
        return item


class ZhuanLanSpider(scrapy.Spider):
    name = 'zhuanlan'
    host = 'https://zhuanlan.zhihu.com/'
    start_urls = ['https://zhuanlan.zhihu.com/HicRhodushicsalta']
    api_urls = 'https://zhuanlan.zhihu.com/api/columns/{0}/posts?limit=20&offset={1}'
    column_api_url = 'https://zhuanlan.zhihu.com/api/columns/{slug}'
    offset = 0
    total = 0
    url_name = ''
    column = None
    creator = None

    custom_settings = {
        'ITEM_PIPELINES': {
            # 'Shadow.pipelines.CheckAvailablePipeline': 200,
            'Shadow.pipelines.ArticleDataStorePipeline': 300,
            # 'Shadow.pipelines.WechatSenderPipeline': 400,
        },
        'DOWNLOADER_MIDDLEWARES': {
            'Shadow.middlewares.UserAgentMiddleware': 1,
            # 'Shadow.middlewares.ProxyMiddleware': 2,
        },
        'COOKIES_ENABLED': False,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS': 1
    }

    # def __init__(self, *args, **kwargs):
    #     session = DBSession()
    #     self.obj = session.query(ZHRandomColumn).first()
    #     if self.obj:
    #         self.start_urls = [self.obj.link]
    #         session.close()
    #     else:
    #         session.close()
    #         raise CloseSpider("No random column item to crawling")
    #     self.start_urls = ['https://zhuanlan.zhihu.com/chuapp']
    #     super(ZhuanLanSpider, self).__init__(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        self.session = DBSession()
        self.obj = None
        super(ZhuanLanSpider, self).__init__(*args, **kwargs)

    def start_requests(self):
        while 1:
            self.obj = self.session.query(ZHRandomColumn).first()
            if self.obj:
                self.start_urls = [self.obj.link]
                yield self.make_requests_from_url(self.obj.link)
            else:
                break
        self.session.close()
        raise CloseSpider("No item to crawling")

    def modify_obj(self):
        if self.obj:
            try:
                self.session.delete(self.obj)
                self.session.commit()
                self.offset = 0
            except Exception as e:
                logging.exception(e)
                self.session.rollback()
                self.session.close()
                self.session = DBSession()

    def get_zhuanlan_name(self):
        self.url_name = self.start_urls[0].strip('/').split('/')[-1]
        return self.url_name

    def generate_api_url(self, offset):
        self.get_zhuanlan_name()
        self.offset += offset
        return self.api_urls.format(self.url_name, self.offset)

    def get_client_config(self, response):
        matchs = re.findall(r'<textarea id="clientConfig" hidden="">(.*?)</textarea>', response.body)
        html_parser = HTMLParser.HTMLParser()
        unescape_data = html_parser.unescape(matchs[0])
        data = json.loads(unescape_data)
        return data

    def parse(self, response):
        if response.status == 404:
            self.modify_obj()
        data = self.get_client_config(response)
        tokens = data.get('tokens')
        headers = response.headers
        headers['referer'] = response.url
        headers['authorization'] = tokens.get('Authorization')
        headers['x-xsrf-token'] = tokens.get('X-XSRF-TOKEN')
        url = self.generate_api_url(0)
        yield Request(url, headers=headers, callback=self.parse_api_result)
        url = self.column_api_url.format(slug=self.get_zhuanlan_name())
        yield Request(url, headers=headers, callback=self.parse_column_info)
        self.modify_obj()

    def parse_column_info(self, response):
        data = json.loads(response.body)
        item = ZHColumnItem()
        slug = data.get('slug')
        self.total = int(data.get('postsCount', 0))
        item['name'] = data.get('name')
        item['link'] = 'https://zhuanlan.zhihu.com/{0}'.format(slug)
        item['hash'] = md5('{0}'.format(slug))
        item['slug'] = slug
        item['description'] = data.get('description')
        item['avatar'] = data.get('avatar').get('template',
                                                'https://pic2.zhimg.com/{id}_{size}.jpg').format(
            id=data.get('avatar').get('id'), size='l')
        self.column = item.copy()
        creator = data.get('creator')
        if creator:
            item = ZHUserItem()
            item['zuid'] = creator.get('uid')
            item['name'] = creator.get('name')
            item['link'] = creator.get('profileUrl')
            item['hash'] = creator.get('hash')
            item['slug'] = creator.get('slug')
            item['description'] = creator.get('description')
            item['headline'] = creator.get('bio')
            item['avatar'] = creator.get('avatar').get('template',
                                                       'https://pic1.zhimg.com/{id}_{size}.jpg').format(
                id=creator.get('avatar').get('id'), size='l')
            self.creator = item.copy()

    def parse_api_result(self, response):
        offset = int(response.url.split('&')[-1].split('=')[-1])
        data = json.loads(response.body)
        for article in data:
            item = ZHCombinationItem()
            author = article.get('author', None)
            link = 'https://zhuanlan.zhihu.com/p/{0}'.format(article.get('slug'))
            item.article['title'] = article.get('title')
            item.article['content'] = article.get('content')
            item.article['summary'] = article.get('summary')
            item.article['cover'] = article.get('titleImage')
            item.article['token'] = article.get('slug')
            item.article['link'] = link
            item.article['md5'] = md5('{0}'.format(item.article['token']))
            item.article['create_time'] = article.get('publishedTime')
            item.article['modify_time'] = article.get('publishedTime')
            if author.get('hash') == self.creator['hash']:
                item.author = self.creator.copy()
            else:
                item.author['zuid'] = author.get('uid')
                item.author['name'] = author.get('name')
                item.author['link'] = author.get('profileUrl')
                item.author['hash'] = author.get('hash')
                item.author['slug'] = author.get('slug')
                item.author['description'] = author.get('description')
                item.author['headline'] = author.get('headline')
                item.author['avatar'] = author.get('avatar').get('template',
                                                                 'https://pic1.zhimg.com/{id}_{size}.jpg').format(
                    id=author.get('avatar').get('id'), size='l')
            item.column = self.column
            item.creator = self.creator
            yield item
        if offset < self.total:
            url = self.generate_api_url(20)
            yield Request(url, callback=self.parse_api_result, headers=response.headers)


class TopZhuanLanSpider(ZhuanLanSpider):
    name = 'topzl'
    exist = False

    custom_settings = {
        'ITEM_PIPELINES': {
            'Shadow.pipelines.IncrementArticleDataStorePipeline': 300,
        },
        'DOWNLOADER_MIDDLEWARES': {
            'Shadow.middlewares.UserAgentMiddleware': 1,
        },
        'COOKIES_ENABLED': False,
        'DOWNLOAD_DELAY': 0.1,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
    }

    def __init__(self, *args, **kwargs):
        self.redis = redis.StrictRedis(host='localhost', port=6379, db=1)
        self.slug = None
        super(ZhuanLanSpider, self).__init__(*args, **kwargs)

    def start_requests(self):
        while 1:
            self.slug = self.redis.spop('top_column_slug')
            if self.slug:
                link = 'https://zhuanlan.zhihu.com/{0}'.format(self.slug)
                self.start_urls = [link]
                self.exist = False
                yield self.make_requests_from_url(link)
            else:
                break
        raise CloseSpider("No top column to crawling")

    def modify_obj(self):
        self.offset = 0

    def parse_api_result(self, response):
        offset = int(response.url.split('&')[-1].split('=')[-1])
        data = json.loads(response.body)
        for article in data:
            item = ZHCombinationItem()
            author = article.get('author', None)
            link = 'https://zhuanlan.zhihu.com/p/{0}'.format(article.get('slug'))
            item.article['title'] = article.get('title')
            item.article['content'] = article.get('content')
            item.article['summary'] = article.get('summary')
            item.article['cover'] = article.get('titleImage')
            item.article['token'] = article.get('slug')
            item.article['link'] = link
            item.article['md5'] = md5('{0}'.format(item.article['token']))
            item.article['create_time'] = article.get('publishedTime')
            item.article['modify_time'] = article.get('publishedTime')
            if author.get('hash') == self.creator['hash']:
                item.author = self.creator.copy()
            else:
                item.author['zuid'] = author.get('uid')
                item.author['name'] = author.get('name')
                item.author['link'] = author.get('profileUrl')
                item.author['hash'] = author.get('hash')
                item.author['slug'] = author.get('slug')
                item.author['description'] = author.get('description')
                item.author['headline'] = author.get('headline')
                item.author['avatar'] = author.get('avatar').get('template',
                                                                 'https://pic1.zhimg.com/{id}_{size}.jpg').format(
                    id=author.get('avatar').get('id'), size='l')
            item.column = self.column
            item.creator = self.creator
            yield item
        if offset < self.total and not self.exist:
            url = self.generate_api_url(20)
            yield Request(url, callback=self.parse_api_result, headers=response.headers)


class RandomFetchSpider(scrapy.Spider):
    name = 'random'
    host = 'https://zhuanlan.zhihu.com/'
    start_urls = ['https://zhuanlan.zhihu.com/']
    random_api_url = 'https://zhuanlan.zhihu.com/api/recommendations/columns?limit={limit}&offset={offset}&seed={seed}'

    custom_settings = {
        'ITEM_PIPELINES': {
            # 'Shadow.pipelines.CheckAvailablePipeline': 200,
            'Shadow.pipelines.RandomColumnPipeline': 300,
        },
        'DOWNLOADER_MIDDLEWARES': {
            'Shadow.middlewares.UserAgentMiddleware': 1,
            # 'Shadow.middlewares.ProxyMiddleware': 2,
        },
        'COOKIES_ENABLED': False,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'DOWNLOAD_DELAY': 2
    }

    def generate_url(self):
        limit = random.randint(13, 40)
        offset = random.randint(0, 100)
        seed = random.randint(0, 100)
        return self.random_api_url.format(limit=limit, offset=offset, seed=seed)

    def parse_random_item(self, response):
        data = json.loads(response.body)
        for itm in data:
            item = ColumnItem()
            item['slug'] = itm.get('slug', '')
            item['link'] = 'https://zhuanlan.zhihu.com/{0}'.format(item['slug'])
            item['hash'] = md5(item['slug'])
            yield item

    def parse(self, response):
        headers = dict()
        headers['referer'] = response.url
        for i in xrange(10):
            url = self.generate_url()
            yield Request(url, headers=headers, callback=self.parse_random_item)
