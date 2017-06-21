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
from models import DBSession, Proxy, ZHArticle, ZHColumn, ZHUser, ZHArticleTagRef, Tag


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
        self.session.flush()
        self.session.commit()
        self.session.close()


class ArticleDataStorePipeline(object):
    def __init__(self):
        self.now = datetime.datetime.now()
        self.session = None
        super(ArticleDataStorePipeline, self).__init__()

    def open_spider(self, spider):
        self.session = DBSession()

    def close_spider(self, spider):
        self.session.flush()
        self.session.commit()
        self.session.close()

    def check_exist(self, md5):
        exist = self.session.query(ZHArticle).filter(ZHArticle.md5 == md5).first()
        return True if exist else False

    def check_column_exist(self, md5):
        exist = self.session.query(ZHColumn).filter(ZHColumn.hash == md5).first()
        return exist if exist else False

    def check_user_exist(self, md5):
        exist = self.session.query(ZHUser).filter(ZHUser.hash == md5).first()
        return exist if exist else False

    def check_tag_exist(self, name):
        exist = self.session.query(Tag).filter(Tag.name == name).first()
        return exist if exist else False

    def create_column(self, item, creator_id=None):
        column = ZHColumn(name=item['name'], link=item['link'], hash=item['hash'], slug=item['slug'],
                          description=item['description'], avatar=item['avatar'], creator_id=creator_id,
                          create_time=self.now, modify_time=self.now)
        self.session.add(column)
        self.session.flush()
        return column

    def create_user(self, item):
        user = ZHUser(zuid=item['zuid'], name=item['name'], link=item['link'], hash=item['hash'], slug=item['slug'],
                      description=item['description'], headline=item['headline'], avatar=item['avatar'],
                      create_time=self.now,
                      modify_time=self.now)
        self.session.add(user)
        self.session.flush()
        return user

    def create_tag(self, name):
        tag = Tag(name=name, create_time=self.now, modify_time=self.now)
        self.session.add(tag)
        self.session.flush()
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
        self.session.flush()
        return article

    def process_item(self, item, spider):
        if not self.check_exist(item.article['md5']):
            column = self.check_column_exist(item.column['hash'])
            author = self.check_user_exist(item.author['hash'])
            if not author:
                author = self.create_user(item.author)
            if author.hash == item.creator['hash']:
                creator = author
            else:
                creator = self.check_user_exist(item.creator['hash'])
                if not creator:
                    creator = self.create_user(item.creator)
            if not column:
                column = self.create_column(item.column, creator.id)
            article = self.create_article(item.article, author.id, column.id)
            tag_list = self.fetch_tags(item.tags)
            self.create_tag_ref(tag_list, article.id)
        return item
