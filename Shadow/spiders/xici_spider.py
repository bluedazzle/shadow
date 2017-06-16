# coding: utf-8

from __future__ import unicode_literals
import scrapy

# from scrapy.selector import HtmlXPathSelector
from scrapy import Selector
from scrapy.http import Request
from Shadow.utils import md5
from Shadow.items import ProxyItem


class XiciProxySpider(scrapy.Spider):
    name = 'xici_spider'
    host = 'http://www.xicidaili.com/'
    start_urls = ['http://www.xicidaili.com/nn/1', 'http://www.xicidaili.com/nn/2', 'http://www.xicidaili.com/nn/3']

    def parse(self, response):
        for sel in response.xpath('//tr')[1:]:
            item = ProxyItem()
            item['host'] = sel.xpath('td[2]/text()').extract()[0].strip()
            item['port'] = sel.xpath('td[3]/text()').extract()[0].strip()
            item['protocol'] = sel.xpath('td[6]/text()').extract()[0].strip()
            # print(item)
            yield item
