# coding: utf-8

from __future__ import unicode_literals

import re
import json
import scrapy
import logging
import HTMLParser

from scrapy import Request
from scrapy.exceptions import CloseSpider
from scrapy import signals
from Shadow.items import ZHUserItem, ColumnItem
from lg_data.db.models import DBSession, ZHUser
from lg_data.utils import md5


class DataBaseRunMixin(object):
    # def start_requests(self):
    #     """Returns a batch of start requests from database."""
    #     req = self.next_requests()
    #     return req.next()

    def fetch_obj(self):
        pass

    def modify_obj(self, obj):
        pass

    def next_requests(self):
        while 1:
            # import pudb;pu.db
            try:
                self.user = self.fetch_obj()
            except Exception as e:
                logging.exception(e)
                self.session.rollback()
                self.session.close()
                self.session = DBSession()
            if not self.user:
                self.session.close()
                break
                # raise CloseSpider('No available user follow to crawl, spider exit')
            req = self.make_requests_from_url('https://zhuanlan.zhihu.com/p/20580194')
            yield req

    def schedule_next_requests(self):
        """Schedules a request if available"""
        if self.user:
            try:
                self.user = self.modify_obj(self.user)
                self.session.commit()
            except Exception as e:
                logging.exception(e)
                self.session.rollback()
                self.session.close()
                self.session = DBSession()
        for req in self.next_requests():
            self.crawler.engine.crawl(req, spider=self)

    def spider_idle(self):
        """Schedules a request if available, otherwise waits."""
        # XXX: Handle a sentinel to close the spider.
        self.schedule_next_requests()
        # raise DontCloseSpider

    def setup_database(self, crawler=None):
        self.session = DBSession()
        if crawler is None:
            # We allow optional crawler argument to keep backwards
            # compatibility.
            # XXX: Raise a deprecation warning.
            crawler = getattr(self, 'crawler', None)

        if crawler is None:
            raise ValueError("crawler is required")
        crawler.signals.connect(self.spider_idle, signal=signals.spider_idle)


class ZHPeopleFollowsSpider(scrapy.Spider):
    name = 'follow'
    host = 'https://www.zhihu.com/'
    start_urls = ['https://zhuanlan.zhihu.com/p/20580194']
    user_follower_api = 'https://www.zhihu.com/api/v4/members/{slug}/followers?limit=20&offset={offset}'
    user_followee_api = 'https://www.zhihu.com/api/v4/members/{slug}/followees?limit=20&offset={offset}'
    response = None
    headers = {}

    custom_settings = {
        'ITEM_PIPELINES': {
            # 'Shadow.pipelines.CheckAvailablePipeline': 200,
            'Shadow.pipelines.UserStorePipeline': 300,
        },
        'DOWNLOADER_MIDDLEWARES': {
            'Shadow.middlewares.UserAgentMiddleware': 1,
            # 'Shadow.middlewares.ProxyMiddleware': 2,

        },
        'COOKIES_ENABLED': False,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'DOWNLOAD_DELAY': 3,
        'CONCURRENT_REQUESTS': 1
    }

    def __init__(self, *args, **kwargs):
        self.session = DBSession()
        self.user = None
        # self.user = self.session.query(ZHUser).filter(ZHUser.crawl_follow == False).first()
        # if not self.user:
        #     raise CloseSpider('No available user follow to crawl, spider exit')
        # self.user.crawl_follow = True
        # self.session.commit()
        super(ZHPeopleFollowsSpider, self).__init__(*args, **kwargs)

    def fetch_obj(self):
        self.user = self.session.query(ZHUser).filter(ZHUser.crawl_follow == False).first()
        return self.user

    def modify_obj(self):
        if self.user:
            self.user.crawl_follow = True
            self.session.commit()
        return self.user

    def start_requests(self):
        while 1:
            url = self.start_urls[0]
            if self.fetch_obj():
                yield self.make_requests_from_url(url)
            else:
                break
        raise CloseSpider('No available user item to crawl follows')

    def get_client_config(self, response):
        matchs = re.findall(r'<textarea id="clientConfig" hidden="">(.*?)</textarea>', response.body)
        html_parser = HTMLParser.HTMLParser()
        unescape_data = html_parser.unescape(matchs[0])
        data = json.loads(unescape_data)
        return data

    def parse(self, response):
        data = self.get_client_config(response)
        tokens = data.get('tokens')
        headers = response.headers
        headers['referer'] = response.url
        headers['authorization'] = tokens.get('Authorization')
        headers['x-xsrf-token'] = tokens.get('X-XSRF-TOKEN')
        self.headers = headers
        url = self.user_follower_api.format(slug=self.user.slug, offset=0)
        yield Request(url, callback=self.parse_follow, headers=self.headers)
        url = self.user_followee_api.format(slug=self.user.slug, offset=0)
        yield Request(url, callback=self.parse_follow, headers=headers)
        self.modify_obj()
        # self.session.close()

    def parse_follow(self, response):
        data = json.loads(response.body)
        pagination = data.get('paging')
        followers = data.get('data', [])
        for follower in followers:
            item = ZHUserItem()
            item['avatar'] = follower.get('avatar_url')
            item['name'] = follower.get('name')
            item['zuid'] = follower.get('id')
            item['slug'] = follower.get('url_token')
            item['hash'] = md5(item['slug'])
            item['headline'] = follower.get('headline')
            item['link'] = 'https://www.zhihu.com/people/{0}'.format(item['slug'])
            item['description'] = ''
            yield item
        is_end = pagination.get('is_end')
        if not is_end:
            url = pagination.get('next')
            yield Request(url, callback=self.parse_follow, headers=self.headers)


class ZHPeopleColumnSpider(scrapy.Spider):
    name = 'column'
    host = 'https://www.zhihu.com/'
    start_urls = ['https://zhuanlan.zhihu.com/p/20580194']
    user_column_api = 'https://www.zhihu.com/api/v4/members/{slug}/column-contributions?limit=20&offset={offset}'
    user_focus_column_api = 'https://www.zhihu.com/api/v4/members/{slug}/following-columns?limit=20&offset={offset}'
    response = None
    headers = {}

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
        'DOWNLOAD_DELAY': 5,
        'CONCURRENT_REQUESTS': 1
    }

    def __init__(self, *args, **kwargs):
        self.session = DBSession()
        self.user = None
        # self.user = self.session.query(ZHUser).filter(ZHUser.crawl_column == False).first()
        # if not self.user:
        #     raise CloseSpider('No available user column to crawl, spider exit')
        # self.user.crawl_column = True
        # self.session.commit()
        super(ZHPeopleColumnSpider, self).__init__(*args, **kwargs)

    def fetch_obj(self):
        self.user = self.session.query(ZHUser).filter(ZHUser.crawl_column == False).first()
        return self.user

    def modify_obj(self):
        if self.user:
            self.user.crawl_column = True
            self.session.commit()
        return self.user

    def start_requests(self):
        while 1:
            url = self.start_urls[0]
            if self.fetch_obj():
                yield self.make_requests_from_url(url)
            else:
                break
        raise CloseSpider('No available user item to crawl columns')

    def get_client_config(self, response):
        matchs = re.findall(r'<textarea id="clientConfig" hidden="">(.*?)</textarea>', response.body)
        html_parser = HTMLParser.HTMLParser()
        unescape_data = html_parser.unescape(matchs[0])
        data = json.loads(unescape_data)
        return data

    def parse(self, response):
        data = self.get_client_config(response)
        tokens = data.get('tokens')
        headers = response.headers
        headers['referer'] = response.url
        headers['authorization'] = tokens.get('Authorization')
        headers['x-xsrf-token'] = tokens.get('X-XSRF-TOKEN')
        self.headers = headers
        if self.user:
            logging.info('Current user is {0}'.format(self.user.slug))
            url = self.user_column_api.format(slug=self.user.slug, offset=0)
            yield Request(url, callback=self.parse_column, headers=self.headers)
            url = self.user_focus_column_api.format(slug=self.user.slug, offset=0)
            yield Request(url, callback=self.parse_focus_column, headers=headers)
            # self.session.close()
            self.modify_obj()

    def parse_column(self, response):
        data = json.loads(response.body)
        pagination = data.get('paging')
        columns = data.get('data', [])
        for column in columns:
            column = column.get('column')
            item = ColumnItem()
            item['slug'] = column.get('id')
            item['hash'] = md5(item['slug'])
            item['link'] = 'https://zhuanlan.zhihu.com/{0}'.format(item['slug'])
            yield item
        is_end = pagination.get('is_end')
        if not is_end:
            url = pagination.get('next')
            yield Request(url, callback=self.parse_column, headers=self.headers)

    def parse_focus_column(self, response):
        data = json.loads(response.body)
        pagination = data.get('paging')
        columns = data.get('data', [])
        for column in columns:
            item = ColumnItem()
            item['slug'] = column.get('id')
            item['hash'] = md5(item['slug'])
            item['link'] = 'https://zhuanlan.zhihu.com/{0}'.format(item['slug'])
            yield item
        is_end = pagination.get('is_end')
        if not is_end:
            url = pagination.get('next')
            yield Request(url, callback=self.parse_focus_column, headers=self.headers)
