# coding: utf-8

from __future__ import unicode_literals
import scrapy

from Shadow.items import ProxyItem


class KuaiProxySpider(scrapy.Spider):
    name = 'kuai_spider'
    host = 'http://www.kuaidaili.com/free/inha/'
    start_urls = ['http://www.kuaidaili.com/free/inha/1/', 'http://www.kuaidaili.com/free/inha/2/',
                  'http://www.kuaidaili.com/free/inha/3/']

    def parse(self, response):
        for sel in response.xpath('//tr')[1:]:
            item = ProxyItem()
            item['host'] = sel.xpath('td[1]/text()').extract()[0].strip()
            item['port'] = sel.xpath('td[2]/text()').extract()[0].strip()
            item['protocol'] = sel.xpath('td[4]/text()').extract()[0].strip()
            yield item
