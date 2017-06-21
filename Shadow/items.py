# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class ProxyItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    host = scrapy.Field()
    port = scrapy.Field()
    protocol = scrapy.Field()


class ZHArticleItem(scrapy.Item):
    title = scrapy.Field()
    content = scrapy.Field()
    summary = scrapy.Field()
    md5 = scrapy.Field()
    token = scrapy.Field()
    cover = scrapy.Field()
    link = scrapy.Field()
    create_time = scrapy.Field()
    modify_time = scrapy.Field()


class ZHColumnItem(scrapy.Item):
    create_time = scrapy.Field()
    modify_time = scrapy.Field()
    name = scrapy.Field()
    link = scrapy.Field()
    hash = scrapy.Field()
    slug = scrapy.Field()
    description = scrapy.Field()
    avatar = scrapy.Field()


class ZHUserItem(scrapy.Item):
    zuid = scrapy.Field()
    create_time = scrapy.Field()
    modify_time = scrapy.Field()
    name = scrapy.Field()
    link = scrapy.Field()
    hash = scrapy.Field()
    slug = scrapy.Field()
    description = scrapy.Field()
    headline = scrapy.Field()
    avatar = scrapy.Field()


class TagItem(scrapy.Item):
    create_time = scrapy.Field()
    modify_time = scrapy.Field()
    name = scrapy.Field()


class ZHCombinationItem(scrapy.Item):
    article = ZHArticleItem()
    author = ZHUserItem()
    creator = ZHUserItem()
    column = ZHColumnItem()
    tags = []
