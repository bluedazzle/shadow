# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
from __future__ import unicode_literals

import datetime

import requests
from scrapy.exceptions import DropItem

from Shadow.const import ProtocolChoice
from models import DBSession, Proxy, ZHArticle


class CheckAvailablePipeline(object):
    url = 'https://www.baidu.com'

    def _process_proxy(self, item):
        proxy = {item['protocol'].lower(): '{0}:{1}'.format(item['host'], item['port'])}
        return proxy

    def process_item(self, item, spider):
        try:
            resp = requests.get(self.url, proxies=self._process_proxy(item), timeout=2)
        except Exception as e:
            raise DropItem("check availbale failed: {0} reason: {1}".format(item, e))
        if resp.status_code != 200:
            raise DropItem("check available failed: %s" % item)
        return item


class ProxyDataStorePipeline(object):
    def open_spider(self, spider):
        self.session = DBSession()

    def process_item(self, item, spider):
        now = datetime.datetime.now()
        host = item['host']
        exist_proxy = self.session.query(Proxy).filter(Proxy.host == host).first()
        if exist_proxy:
            exist_proxy.available = True
        else:
            proxy = Proxy(host=item['host'], port=item['port'], create_time=now, modify_time=now, available=True)
            if item['protocol'].upper() == 'HTTP':
                proxy.protocol = ProtocolChoice.HTTP.value
            else:
                proxy.protocol = ProtocolChoice.HTTPS.value
            self.session.add(proxy)
        return item

    def close_spider(self, spider):
        self.session.flush()
        self.session.commit()
        self.session.close()


class ArticleDataStorePipeline(object):
    def open_spider(self, spider):
        self.session = DBSession()

    def close_spider(self, spider):
        self.session.flush()
        self.session.commit()
        self.session.close()

    def check_exist(self, md5):
        exist = self.session.query(ZHArticle).filter(ZHArticle.md5 == md5).first()
        return True if exist else False

    def process_item(self, item, spider):
        if not self.check_exist(item['md5']):
            article = ZHArticle(title=item['title'], content=item['content'], cover=item['cover'], md5=item['md5'],
                                link=item['link'], token=item['token'], summary=item['summary'])
            article.create_time = datetime.datetime.strptime(item['create_time'], '%Y-%m-%dT%H:%M:%S+08:00')
            article.modify_time = datetime.datetime.strptime(item['modify_time'], '%Y-%m-%dT%H:%M:%S+08:00')
            self.session.add(article)
        return item
