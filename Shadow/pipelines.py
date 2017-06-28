# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
from __future__ import unicode_literals

import datetime

import logging
import requests
from scrapy.exceptions import DropItem
from wechat_sender import Sender

from Shadow.const import ProtocolChoice
from models import DBSession, Proxy, ZHArticle, ZHColumn, ZHUser, ZHArticleTagRef, Tag, ZHRandomColumn

logger = logging.getLogger('scrapy')


class DataStorePipelineBase(object):
    def __init__(self):
        self.now = datetime.datetime.now()
        self.session = None
        super(DataStorePipelineBase, self).__init__()

    def open_spider(self, spider):
        self.session = DBSession()

    def close_spider(self, spider):
        try:
            self.session.flush()
            self.session.commit()
        except Exception as e:
            logger.exception(e)
            self.session.rollback()
        finally:
            self.session.close()


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


class ArticleDataStorePipeline(object):
    def __init__(self):
        self.now = datetime.datetime.now()
        self.session = None
        super(ArticleDataStorePipeline, self).__init__()

    def open_spider(self, spider):
        self.session = DBSession()

    def close_spider(self, spider):
        try:
            self.session.delete(spider.obj)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            logger.exception(e)
        finally:
            self.session.close()

    def check_exist(self, md5):
        exist = self.session.query(ZHArticle).filter(ZHArticle.md5 == md5).first()
        return True if exist else False

    def check_column_exist(self, md5):
        exist = self.session.query(ZHColumn).filter(ZHColumn.hash == md5).first()
        return exist if exist else False

    def check_user_exist(self, md5):
        exist = self.session.query(ZHUser).filter(ZHUser.slug == md5).first()
        return exist if exist else False

    def check_tag_exist(self, name):
        exist = self.session.query(Tag).filter(Tag.name == name).first()
        return exist if exist else False

    def create_column(self, item, creator_id=None):
        column = ZHColumn(name=item['name'], link=item['link'], hash=item['hash'], slug=item['slug'],
                          description=item['description'], avatar=item['avatar'], creator_id=creator_id,
                          create_time=self.now, modify_time=self.now)
        self.session.add(column)
        self.session.commit()
        return column

    def create_user(self, item):
        user = ZHUser(zuid=item['zuid'], name=item['name'], link=item['link'], hash=item['hash'], slug=item['slug'],
                      description=item['description'], headline=item['headline'], avatar=item['avatar'],
                      create_time=self.now,
                      modify_time=self.now)

        try:
            self.session.add(user)
            self.session.commit()
        except Exception as e:
            logging.exception(e)
            self.session.rollback()
            self.session.close()
            self.session = DBSession()
            #user = self.check_user_exist(item['hash'])
        return user

    def create_tag(self, name):
        tag = Tag(name=name, create_time=self.now, modify_time=self.now)
        self.session.add(tag)
        self.session.commit()
        return tag

    def fetch_tag(self, name):
        tag = self.check_tag_exist(name)
        if not tag:
            tag = self.create_tag(name)
        return tag

    def fetch_tags(self, tags):
        tag_list = []
        for tag in tags:
            tag = self.fetch_tag(tag['name'])
            tag_list.append(tag)
        return tag_list

    def create_tag_ref(self, tag_list, article_id):
        for tag in tag_list:
            self.session.add(ZHArticleTagRef(zharticle_id=article_id, tag_id=tag.id))

    def create_article(self, item, author_id, column_id):
        article = ZHArticle(title=item['title'], content=item['content'],
                            cover=item['cover'], md5=item['md5'],
                            link=item['link'], token=item['token'],
                            summary=item['summary'])
        article.create_time = datetime.datetime.strptime(item['create_time'], '%Y-%m-%dT%H:%M:%S+08:00')
        article.modify_time = datetime.datetime.strptime(item['modify_time'], '%Y-%m-%dT%H:%M:%S+08:00')
        article.author_id = author_id
        article.belong_id = column_id
        self.session.add(article)
        self.session.commit()
        return article

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
        return item


class RandomColumnPipeline(object):
    def __init__(self):
        self.now = datetime.datetime.now()
        self.session = None
        super(RandomColumnPipeline, self).__init__()

    def open_spider(self, spider):
        self.session = DBSession()

    def close_spider(self, spider):
        try:
            self.session.flush()
            self.session.commit()
        except Exception as e:
            logger.exception(e)
            self.session.rollback()
        finally:
            self.session.close()

    def check_column_exist(self, md5):
        exist = self.session.query(ZHColumn).filter(ZHColumn.hash == md5).first()
        if exist:
            return exist
        exist = self.session.query(ZHRandomColumn).filter(ZHRandomColumn.hash == md5).first()
        return exist if exist else False

    def create_random_column(self, item):
        column = ZHRandomColumn(link=item['link'], slug=item['slug'], hash=item['hash'])
        column.create_time = self.now
        column.modify_time = self.now
        self.session.add(column)
        self.session.commit()

    def process_item(self, item, spider):
        self.now = datetime.datetime.now()
        if item['hash'] != '':
            res = self.check_column_exist(item['hash'])
            if not res:
                self.create_random_column(item)
            else:
                raise DropItem('Item already exist {0}'.format(item))
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
    def check_user_exist(self, md5):
        res = self.session.query(ZHUser).filter(ZHUser.slug == md5).first()
        return res if res else False

    def create_user(self, item):
        user = ZHUser(zuid=item['zuid'], name=item['name'], link=item['link'], hash=item['hash'], slug=item['slug'],
                      description=item['description'], headline=item['headline'], avatar=item['avatar'],
                      create_time=self.now,
                      modify_time=self.now)
        try:
            self.session.add(user)
            self.session.commit()
        except Exception as e:
            logging.exception(e)
            self.session.rollback()
            self.session.close()
            self.session = DBSession()
        return user

    def process_item(self, item, spider):
        self.now = datetime.datetime.now()
        if self.check_user_exist(item['slug']):
            raise DropItem('User Item already exist {0}'.format(item))
        self.create_user(item)
        return item
