# coding: utf-8

from __future__ import unicode_literals

import json
import re

import scrapy
from scrapy import Request

from Shadow.items import ZHArticleItem, ZHCombinationItem, TagItem, ZHColumnItem, ZHUserItem
from Shadow.utils import md5


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

    def generate_header(self):
        matchs = re.findall(r'<textarea id="clientConfig" hidden>(.*?)</textarea>', self.response.body)
        data = json.loads(matchs[0])
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
        matchs = re.findall(r'<textarea id="preloadedState" hidden>(.*?)</textarea>', response.body)
        data = json.loads(matchs[0])
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
    start_urls = ['https://zhuanlan.zhihu.com/finance']
    api_urls = 'https://zhuanlan.zhihu.com/api/columns/{0}/posts?limit=20&offset={1}'
    column_api_url = 'https://zhuanlan.zhihu.com/api/columns/{slug}'
    offset = 0
    url_name = ''
    column = None
    creator = None

    custom_settings = {
        'ITEM_PIPELINES': {
            # 'Shadow.pipelines.CheckAvailablePipeline': 200,
            'Shadow.pipelines.ArticleDataStorePipeline': 300,
        },
        'DOWNLOADER_MIDDLEWARES': {
            'Shadow.middlewares.UserAgentMiddleware': 1,
            'Shadow.middlewares.ProxyMiddleware': 2,
        },
        'COOKIES_ENABLED': False,
        'CONCURRENT_REQUESTS': 1
    }

    def get_zhuanlan_name(self):
        self.url_name = self.start_urls[0].strip('/').split('/')[-1]
        return self.url_name

    def generate_api_url(self, offset):
        self.get_zhuanlan_name()
        self.offset += offset
        return self.api_urls.format(self.url_name, self.offset)

    def parse(self, response):
        matchs = re.findall(r'<textarea id="clientConfig" hidden>(.*?)</textarea>', response.body)
        data = json.loads(matchs[0])
        tokens = data.get('tokens')
        headers = response.headers
        headers['referer'] = response.url
        headers['authorization'] = tokens.get('Authorization')
        headers['x-xsrf-token'] = tokens.get('X-XSRF-TOKEN')
        url = self.generate_api_url(0)
        yield Request(url, headers=headers, callback=self.parse_api_result)
        url = self.column_api_url.format(slug=self.get_zhuanlan_name())
        yield Request(url, headers=headers, callback=self.parse_column_info)

    def parse_column_info(self, response):
        data = json.loads(response.body)
        item = ZHColumnItem()
        slug = data.get('slug')
        item['name'] = data.get('name')
        item['link'] = 'https://zhuanlan.zhihu.com/{0}'.format(slug)
        item['hash'] = md5('{0}'.format(slug))
        item['slug'] = slug
        item['description'] = data.get('description')
        item['avatar'] = data.get('avatar').get('template',
                                                'https://pic2.zhimg.com/{id}_{size}.jpg').format(
            id=data.get('avatar').get('id'), size='l')
        self.column = item
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
            self.creator = item

    def parse_api_result(self, response):
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
            item.column = self.column.copy()
            item.creator = self.creator.copy()
            yield item
        if len(data) == 20:
            url = self.generate_api_url(20)
            yield Request(url, callback=self.parse_api_result, headers=response.headers)


class RandomFetchSpider(scrapy.Spider):
    name = 'random'
    host = 'https://zhuanlan.zhihu.com/'

    custom_settings = {
        'ITEM_PIPELINES': {
            # 'Shadow.pipelines.CheckAvailablePipeline': 200,
            'Shadow.pipelines.ArticleDataStorePipeline': 300,
        },
        'DOWNLOADER_MIDDLEWARES': {
            'Shadow.middlewares.UserAgentMiddleware': 1,
            'Shadow.middlewares.ProxyMiddleware': 2,
        },
        'COOKIES_ENABLED': False,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'DOWNLOAD_DELAY': 10
    }
