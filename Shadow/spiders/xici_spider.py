# coding: utf-8

from __future__ import unicode_literals
import scrapy

from Shadow.items import ProxyItem


class XiciProxySpider(scrapy.Spider):
    name = 'xici_spider'
    host = 'http://www.xicidaili.com/'
    start_urls = ['http://www.xicidaili.com/nn/1']
    # start_urls = ['http://www.xicidaili.com/nn/1', 'http://www.xicidaili.com/nn/2', 'http://www.xicidaili.com/nn/3']

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
            item['host'] = sel.xpath('td[2]/text()').extract()[0].strip()
            item['port'] = sel.xpath('td[3]/text()').extract()[0].strip()
            item['protocol'] = sel.xpath('td[6]/text()').extract()[0].strip()
            yield item
