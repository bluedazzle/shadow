# coding: utf-8

from __future__ import unicode_literals

import json
import re

import scrapy

from Shadow.items import ZHArticleItem
from Shadow.utils import md5


class ZhuanLanSpider(scrapy.Spider):
    name = 'zhuanlan_spider'
    host = 'https://zhuanlan.zhihu.com/'
    start_urls = ['https://zhuanlan.zhihu.com/p/27152885']

    custom_settings = {
        'ITEM_PIPELINES': {
            # 'Shadow.pipelines.CheckAvailablePipeline': 200,
            'Shadow.pipelines.ArticleDataStorePipeline': 300,
        },
        'DOWNLOADER_MIDDLEWARES': {
            'Shadow.middlewares.UserAgentMiddleware': 1,
        },
        'COOKIES_ENABLED': False,
    }

    def parse(self, response):
        matchs = re.findall(r'<textarea id="preloadedState" hidden>(.*?)</textarea>', response.body)
        data = json.loads(matchs[0])
        item = ZHArticleItem()
        article_data = data.get('database').get('Post').values()[0]
        link = 'https://zhuanlan.zhihu.com/p/{0}'.format(article_data.get('slug'))
        item['title'] = article_data.get('title')
        item['content'] = article_data.get('content')
        item['summary'] = article_data.get('summary')
        item['cover'] = article_data.get('titleImage')
        item['token'] = article_data.get('slug')
        item['md5'] = md5(item['token'])
        item['link'] = link
        item['token'] = article_data.get('slug')
        item['create_time'] = article_data.get('publishedTime')
        item['modify_time'] = article_data.get('publishedTime')
        yield item
