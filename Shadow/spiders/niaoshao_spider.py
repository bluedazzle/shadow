# coding: utf-8

from __future__ import unicode_literals
import scrapy

from Shadow.items import ProxyItem


class NiaoShaoProxySpider(scrapy.Spider):
    name = 'niaoshao_spider'
    host = 'http://www.xicidaili.com/'
    start_urls = ['http://www.nianshao.me/?stype=1', 'http://www.nianshao.me/?stype=1&page=2',
                  'http://www.nianshao.me/?stype=1&page=3', 'http://www.nianshao.me/?stype=2',
                  'http://www.nianshao.me/?stype=2&page=2', 'http://www.nianshao.me/?stype=2&page=3']

    custom_settings = {
        'ITEM_PIPELINES': {
            'Shadow.pipelines.CheckAvailablePipeline': 200,
            'Shadow.pipelines.ProxyDataStorePipeline': 300,
        },
        'DOWNLOADER_MIDDLEWARES': {
            'Shadow.middlewares.UserAgentMiddleware': 1,
        },
        'COOKIES_ENABLED': False,
    }

    def parse(self, response):
        for sel in response.xpath('//tr')[1:]:
            item = ProxyItem()
            item['host'] = sel.xpath('td[1]/text()').extract()[0].strip()
            item['port'] = sel.xpath('td[2]/text()').extract()[0].strip()
            item['protocol'] = sel.xpath('td[5]/text()').extract()[0].strip()
            # print(item)
            yield item
