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
import random
from scrapy.exceptions import DropItem
from wechat_sender import Sender
from bs4 import BeautifulSoup

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
            self.session.commit()
        except Exception as e:
            logger.exception(e)
            self.session.rollback()
        finally:
            self.session.close()


class ArticleDataStorePipeline(DataStorePipelineBase):
    user_cache_count = 0
    column_cache_count = 0

    def __init__(self):
        super(ArticleDataStorePipeline, self).__init__()
        self.tmp_session = DBSession()

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

    def get_id(self, model, id_type=1):
        if id_type == 1:
            if self.user_cache_count != 0:
                self.user_cache_count += 1
                return self.user_cache_count
            else:
                obj = self.session.query(model.id).order_by(model.id.desc()).first()
                self.user_cache_count = obj[0] + 1
                return self.user_cache_count
        else:
            if self.column_cache_count != 0:
                self.column_cache_count += 1
                return self.column_cache_count
            else:
                obj = self.session.query(model.id).order_by(model.id.desc()).first()
                self.column_cache_count = obj[0] + 1
                return self.column_cache_count

    #
    # def check_exist(self, md5):
    #     exist = self.session.query(ZHArticle.id).filter(ZHArticle.md5 == md5).first()
    #     return True if exist[0] else False
    #
    def check_column_exist(self, md5):
        exist = self.session.query(ZHColumn).filter(ZHColumn.hash == md5).first()
        return exist if exist else False

    def check_user_exist(self, md5):
        exist = self.session.query(ZHUser).filter(ZHUser.slug == md5).first()
        return exist if exist else False

    # def check_tag_exist(self, name):
    #     exist = self.session.query(Tag.id).filter(Tag.name == name).first()
    #     return exist if exist[0] else False

    def create_column(self, item, creator_id=None):
        self.get_now()
        column = ZHColumn(name=item['name'], link=item['link'],
                          hash=item['hash'],
                          slug=item['slug'],
                          description=item['description'], avatar=item['avatar'], creator_id=creator_id,
                          create_time=self.now, modify_time=self.now)
        self.tmp_session.add(column)
        self.tmp_session.commit()
        return column

    def create_user(self, item):
        self.get_now()
        user = ZHUser(zuid=item['zuid'], name=item['name'], link=item['link'],
                      hash=item['hash'], slug=item['slug'],
                      description=item['description'], headline=item['headline'], avatar=item['avatar'],
                      create_time=self.now,
                      modify_time=self.now)
        self.tmp_session.add(user)
        self.tmp_session.commit()
        return user

    def fix_image(self, item):
        soup = BeautifulSoup(item['content'])
        finds = soup.find_all('img')
        for itm in finds:
            host_random = random.randint(1, 4)
            itm['src'] = 'https://pic{0}.zhimg.com/{1}'.format(host_random, itm['src'])
        if not item['cover']:
            if finds:
                item['cover'] = finds[0]['src']
            else:
                item['cover'] = '/s/image/default.jpg'
        item['content'] = soup.prettify()
        return item

    def create_article(self, item, author_id, column_id):
        item = self.fix_image(item)
        article, new = ZHArticle.as_unique(self.session, title=item['title'], content=item['content'],
                                           cover=item['cover'], md5=item['md5'],
                                           link=item['link'], token=item['token'],
                                           summary=item['summary'], keywords='',
                                           create_time=datetime.datetime.strptime(item['create_time'],
                                                                                  '%Y-%m-%dT%H:%M:%S+08:00'),
                                           modify_time=datetime.datetime.strptime(item['modify_time'],
                                                                                  '%Y-%m-%dT%H:%M:%S+08:00'),
                                           author_id=author_id,
                                           belong_id=column_id)
        return article, new

    def process_item(self, item, spider):
        author = self.check_user_exist(item.author['slug'])
        if not author:
            author = self.create_user(item.author)
        if author.slug == item.creator['slug']:
            creator = author
        else:
            creator = self.check_user_exist(item.creator['slug'])
            if not creator:
                creator = self.create_user(item.creator)
        column = self.check_column_exist(item.column['hash'])
        if not column:
            column = self.create_column(item.column, creator.id)
        article, new = self.create_article(item.article, author.id, column.id)
        if not new:
            raise DropItem('Article item {0} already exist'.format(item.article['title']))
        self.periodic_commit()
        return item

    def periodic_commit(self):
        self.count += 1
        if self.count == 100:
            try:
                logger.info('Periodic commit to database')
                self.count = 0
                self.user_cache_count = 0
                self.column_cache_count = 0
                self.session.commit()
                self.session._unique_cache = None
            except Exception as e:
                logger.exception(e)
                self.session.rollback()


class IncrementArticleDataStorePipeline(ArticleDataStorePipeline):
    pass


class RandomColumnPipeline(DataStorePipelineBase):
    def check_exist(self, item):
        obj = self.session.query(ZHColumn.id).filter(ZHColumn.slug == item['slug'])
        return self.session.query(obj.exists()).scalar()

    def create_random_column(self, item):
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
