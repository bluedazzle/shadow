# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
from __future__ import unicode_literals

import datetime

import logging

import pytz
import requests
from scrapy.exceptions import DropItem
from wechat_sender import Sender

from Shadow.const import ProtocolChoice
from models import DBSession, Proxy, ZHArticle, ZHColumn, ZHUser, ZHArticleTagRef, Tag, ZHRandomColumn

logger = logging.getLogger('scrapy')


class DataStorePipelineBase(object):
    def __init__(self):
        self.now = datetime.datetime.now(tz=pytz.timezone('Asia/Shanghai'))
        self.session = None
        self.count = 0
        super(DataStorePipelineBase, self).__init__()

    def get_now(self):
        self.now = datetime.datetime.now(tz=pytz.timezone('Asia/Shanghai'))
        return self.now

    def open_spider(self, spider):
        self.session = DBSession()

    def close_spider(self, spider):
        try:
            self.session.commit()
            self.session._unique_cache = None
        except Exception as e:
            logger.exception(e)
            self.session.rollback()
        finally:
            self.session.close()

    def periodic_commit(self):
        self.count += 1
        if self.count == 100:
            try:
                logger.info('Periodic commit to database')
                self.count = 0
                self.session.commit()
                self.session._unique_cache = None
            except Exception as e:
                logger.exception(e)
                self.session.rollback()


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
            if item['protocol'].upper() == ProtocolChoice.HTTP:
                proxy.protocol = ProtocolChoice.HTTP
            else:
                proxy.protocol = ProtocolChoice.HTTPS
            self.session.add(proxy)
        return item

    def close_spider(self, spider):
        try:
            self.session.flush()
            self.session.commit()
        except Exception as e:
            logger.exception(e)
            self.session.rollback()
        finally:
            self.session.close()


class ArticleDataStorePipeline(DataStorePipelineBase):
    def close_spider(self, spider):
        try:
            self.session.delete(spider.obj)
            self.session.commit()
            self.session._unique_cache = None
        except Exception as e:
            self.session.rollback()
            logger.exception(e)
        finally:
            self.session.close()

    def get_id(self, model):
        obj = self.session.query(model.id).order_by(model.id.desc()).first()
        return obj[0] + 1
    #
    # def check_exist(self, md5):
    #     exist = self.session.query(ZHArticle.id).filter(ZHArticle.md5 == md5).first()
    #     return True if exist[0] else False
    #
    # def check_column_exist(self, md5):
    #     exist = self.session.query(ZHColumn).filter(ZHColumn.hash == md5).first()
    #     return exist if exist else False
    #
    # def check_user_exist(self, md5):
    #     exist = self.session.query(ZHUser).filter(ZHUser.slug == md5).first()
    #     return exist if exist else False
    #
    # def check_tag_exist(self, name):
    #     exist = self.session.query(Tag.id).filter(Tag.name == name).first()
    #     return exist if exist[0] else False

    def create_column(self, item, creator_id=None):
        self.get_now()
        self.get_id(ZHColumn)
        return ZHColumn.as_unique(self.session, name=item['name'], link=item['link'], hash=item['hash'],
                                  slug=item['slug'],
                                  description=item['description'], avatar=item['avatar'], creator_id=creator_id,
                                  create_time=self.now, modify_time=self.now, id=uid)

    def create_user(self, item):
        self.get_now()
        return ZHUser.as_unique(self.session, zuid=item['zuid'], name=item['name'], link=item['link'],
                                hash=item['hash'], slug=item['slug'],
                                description=item['description'], headline=item['headline'], avatar=item['avatar'],
                                create_time=self.now,
                                modify_time=self.now)

    def create_article(self, item, author_id, column_id):
        article, new = ZHArticle.as_unique(self.session, title=item['title'], content=item['content'],
                                           cover=item['cover'], md5=item['md5'],
                                           link=item['link'], token=item['token'],
                                           summary=item['summary'])
        article.create_time = datetime.datetime.strptime(item['create_time'], '%Y-%m-%dT%H:%M:%S+08:00')
        article.modify_time = datetime.datetime.strptime(item['modify_time'], '%Y-%m-%dT%H:%M:%S+08:00')
        article.author_id = author_id
        article.belong_id = column_id
        return article, new

    def process_item(self, item, spider):
        if self.check_exist(item.article['md5']):
            raise DropItem('Article item {0} already exist'.format(item.article['title']))
        self.now = datetime.datetime.now()
        column = self.check_column_exist(item.column['hash'])
        author = self.check_user_exist(item.author['slug'])
        if not author:
            author = self.create_user(item.author)
        if author.slug == item.creator['slug']:
            creator = author
        else:
            creator = self.check_user_exist(item.creator['slug'])
            if not creator:
                creator = self.create_user(item.creator)
        if not column:
            column = self.create_column(item.column, creator.id)
        article = self.create_article(item.article, author.id, column.id)
        self.periodic_commit()
        return item


class RandomColumnPipeline(DataStorePipelineBase):
    def check_exist(self, item):
        obj = self.session.query(ZHColumn.id).filter(ZHColumn.slug == item['slug'])
        return self.session.query(obj.exists()).scalar()

    def create_random_column(self, item):
        if self.check_exist(item):
            return None, False
        self.get_now()
        return ZHRandomColumn.as_unique(self.session, link=item['link'], slug=item['slug'], hash=item['hash'],
                                        create_time=self.now, modify_time=self.now)

    def process_item(self, item, spider):
        if item['hash'] != '':
            column, new = self.create_random_column(item)
            if not new:
                raise DropItem('Item already exist {0}'.format(item))
        self.periodic_commit()
        return item


class WechatSenderPipeline(object):
    def __init__(self):
        self.now = datetime.datetime.now()
        self.total = 0
        self.sender = Sender('rapospectre', 'rapospectre', 'http://114.215.153.187', port=10245)
        super(WechatSenderPipeline, self).__init__()

    def close_spider(self, spider):
        msg = '[{time:%Y-%m-%d %H:%M:%S}]抓取专栏{slug}文章成功，抓取数目: {count}'.format(count=self.total, time=self.now,
                                                                              slug=spider.obj.slug)
        self.sender.send(msg)

    def process_item(self, item, spider):
        self.total += 1
        return item


class UserStorePipeline(DataStorePipelineBase):
    def create_user(self, item):
        return ZHUser.as_unique(self.session, zuid=item['zuid'], name=item['name'], link=item['link'],
                                hash=item['hash'], slug=item['slug'],
                                description=item['description'], headline=item['headline'], avatar=item['avatar'],
                                create_time=self.now,
                                modify_time=self.now)

    def process_item(self, item, spider):
        user, new = self.create_user(item)
        if not new:
            raise DropItem('User Item already exist {0}'.format(item))
        self.periodic_commit()
        return item
