# -*- coding: utf-8 -*-

# Define here the models for your spider middleware
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/spider-middleware.html
import random

from scrapy import signals

from lg_data.db.models import DBSession, Proxy


class UserAgentMiddleware(object):
    def __init__(self, agents):
        self.agents = agents

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings.getlist('USER_AGENTS'))

    def process_request(self, request, spider):
        request.headers.setdefault('User-Agent', random.choice(self.agents))


class ProxyMiddleware(object):
    session = None
    proxies = None

    def get_proxy(self):
        self.session = DBSession()
        if not self.proxies:
            self.proxies = self.session.query(Proxy).all()
        count = len(self.proxies)
        index = random.randint(0, count - 1)
        return self.proxies[index]

    def process_request(self, request, spider):
        # proxy = self.get_proxy()
        # if proxy.protocol == ProtocolChoice.HTTP:
        #     request.meta['proxy'] = "http://{host}:{port}".format(host=proxy.host, port=proxy.port)
        # else:
        #     request.meta['proxy'] = "https://{host}:{port}".format(host=proxy.host, port=proxy.port)
        request.meta['proxy'] = "https://10.4.18.169:3128"


class ShadowSpiderMiddleware(object):
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, dict or Item objects.
        for i in result:
            yield i

    def process_spider_exception(response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Response, dict
        # or Item objects.
        pass

    def process_start_requests(start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)
